import hashlib
import logging
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from apps.api.src.db.session import AsyncSessionLocal
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import ProjectStatus, SnapshotStatus
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.github_client import GitHubClient
from apps.api.src.services.parser.dependency_extractor import (
    ExtractedDependency,
    extract_dependencies_from_tree,
)
from apps.api.src.services.parser.heuristics import (
    PARSER_SUPPORTED_LANGUAGES,
    detect_language,
    is_file_binary,
    is_file_generated,
    is_file_test,
    is_path_excluded,
)
from apps.api.src.services.parser.symbol_extractor import extract_symbols_from_tree
from apps.api.src.services.parser.tree_sitter_parser import parse_code

logger = logging.getLogger("unotusk-ingestion")


def utc_now() -> datetime:
    return datetime.now(UTC)


class IngestionService:
    @staticmethod
    async def run_ingestion(
        snapshot_id: uuid.UUID,
        override_local_dir: str | None = None,
    ) -> None:
        """Execute the end-to-end repository ingestion pipeline."""
        async with AsyncSessionLocal() as session:
            # 1. Fetch snapshot & repository
            query = select(RepositorySnapshot).where(RepositorySnapshot.id == snapshot_id)
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()

            if snapshot is None:
                logger.error(f"Ingestion snapshot {snapshot_id} not found.")
                return

            repo_query = select(Repository).where(Repository.id == snapshot.repository_id)
            repo_res = await session.execute(repo_query)
            repository = repo_res.scalar_one_or_none()
            if repository is None:
                logger.error(f"Repository {snapshot.repository_id} not found.")
                return

            # Fetch integration token if present
            from apps.api.src.models.integration import Integration
            int_query = select(Integration).where(Integration.id == repository.integration_id)
            int_res = await session.execute(int_query)
            integration = int_res.scalar_one_or_none()
            github_token = None
            if integration and integration.integration_metadata:
                github_token = integration.integration_metadata.get("github_token")

            # Update status to CLONING
            snapshot.status = SnapshotStatus.CLONING
            snapshot.started_at = utc_now()
            await session.commit()

            temp_dir = None
            try:
                # 2. Retrieval / Clone
                if override_local_dir and os.path.exists(override_local_dir):
                    source_dir = override_local_dir
                    commit_sha = "local-dev-commit"
                else:
                    temp_dir = tempfile.mkdtemp(prefix="unotusk-repo-")
                    client = GitHubClient(token=github_token)
                    commit_sha = client.clone_repository(
                        clone_url=repository.url,
                        target_dir=temp_dir,
                        branch=snapshot.branch,
                    )
                    source_dir = temp_dir

                snapshot.commit_sha = commit_sha
                snapshot.status = SnapshotStatus.SCANNING
                await session.commit()

                # 3. SCANNING: File Discovery
                discovered_files: list[dict] = []
                for root, dirs, files in os.walk(source_dir):
                    rel_dir = os.path.relpath(root, source_dir)
                    if rel_dir != "." and is_path_excluded(rel_dir):
                        dirs.clear()  # Prune excluded subtrees
                        continue

                    # Filter excluded subdirectories
                    dirs[:] = [d for d in dirs if not is_path_excluded(os.path.join(rel_dir, d))]

                    for filename in files:
                        file_rel_path = os.path.normpath(
                            os.path.join(rel_dir, filename) if rel_dir != "." else filename
                        )
                        if is_path_excluded(file_rel_path):
                            continue

                        full_path = os.path.join(root, filename)
                        file_stat = os.stat(full_path)
                        size_bytes = file_stat.st_size
                        ext = os.path.splitext(filename)[1].lower()
                        lang = detect_language(filename)
                        binary = is_file_binary(filename)
                        generated = is_file_generated(filename)
                        is_test = is_file_test(file_rel_path)

                        # Content hash and line count (if text)
                        content_hash = ""
                        line_count = 0
                        content_bytes = b""
                        if not binary and size_bytes < 5_000_000:  # Max 5MB per source file
                            try:
                                with open(full_path, "rb") as f:
                                    content_bytes = f.read()
                                content_hash = hashlib.sha256(content_bytes).hexdigest()
                                line_count = content_bytes.count(b"\n") + (1 if content_bytes else 0)
                            except Exception:
                                binary = True
                        else:
                            content_hash = hashlib.sha256(file_rel_path.encode()).hexdigest()

                        parser_supported = lang in PARSER_SUPPORTED_LANGUAGES and not binary

                        discovered_files.append(
                            {
                                "path": file_rel_path,
                                "filename": filename,
                                "extension": ext,
                                "language": lang,
                                "size_bytes": size_bytes,
                                "content_hash": content_hash,
                                "is_binary": binary,
                                "is_generated": generated,
                                "is_test": is_test,
                                "line_count": line_count,
                                "parser_supported": parser_supported,
                                "content_bytes": content_bytes,
                            }
                        )

                snapshot.total_files = len(discovered_files)
                snapshot.status = SnapshotStatus.PARSING
                await session.commit()

                # 4. PARSING & INDEXING: Persist Files, Symbols, Dependencies
                created_files_map: dict[str, RepositoryFile] = {}
                raw_deps_to_create: list[tuple[uuid.UUID, ExtractedDependency]] = []

                # First pass: create all RepositoryFile records
                for f_info in discovered_files:
                    repo_file = RepositoryFile(
                        id=uuid.uuid4(),
                        snapshot_id=snapshot.id,
                        path=f_info["path"],
                        filename=f_info["filename"],
                        extension=f_info["extension"],
                        language=f_info["language"],
                        size_bytes=f_info["size_bytes"],
                        content_hash=f_info["content_hash"],
                        is_binary=f_info["is_binary"],
                        is_generated=f_info["is_generated"],
                        is_test=f_info["is_test"],
                        line_count=f_info["line_count"],
                        parser_supported=f_info["parser_supported"],
                    )
                    session.add(repo_file)
                    created_files_map[f_info["path"]] = repo_file

                await session.flush()

                # Second pass: Parse AST for symbols and dependencies
                processed_count = 0
                for f_info in discovered_files:
                    repo_file = created_files_map[f_info["path"]]
                    content = f_info["content_bytes"]

                    if f_info["parser_supported"] and content:
                        tree = parse_code(content, f_info["language"])
                        if tree is not None:
                            # Extract symbols
                            extracted_symbols = extract_symbols_from_tree(tree, content, f_info["language"])
                            for sym in extracted_symbols:
                                code_sym = CodeSymbol(
                                    id=uuid.uuid4(),
                                    file_id=repo_file.id,
                                    name=sym.name,
                                    symbol_type=sym.symbol_type,
                                    qualified_name=sym.qualified_name,
                                    start_line=sym.start_line,
                                    end_line=sym.end_line,
                                    symbol_metadata=sym.metadata,
                                )
                                session.add(code_sym)

                                # Children (e.g. methods within class)
                                for child_sym in sym.children:
                                    child_code_sym = CodeSymbol(
                                        id=uuid.uuid4(),
                                        file_id=repo_file.id,
                                        name=child_sym.name,
                                        symbol_type=child_sym.symbol_type,
                                        qualified_name=child_sym.qualified_name,
                                        start_line=child_sym.start_line,
                                        end_line=child_sym.end_line,
                                        parent_symbol_id=code_sym.id,
                                        symbol_metadata=child_sym.metadata,
                                    )
                                    session.add(child_code_sym)

                            # Extract dependencies / imports
                            extracted_deps = extract_dependencies_from_tree(tree, content, f_info["language"])
                            for dep in extracted_deps:
                                raw_deps_to_create.append((repo_file.id, dep))

                    processed_count += 1
                    if processed_count % 50 == 0:
                        snapshot.processed_files = processed_count
                        await session.commit()

                # 5. INDEXING: Link internal dependencies & external packages
                snapshot.status = SnapshotStatus.INDEXING
                await session.commit()

                for source_file_id, dep in raw_deps_to_create:
                    target_file_id = None
                    ext_pkg = None

                    if dep.is_relative:
                        # Attempt to resolve relative import target file
                        # Normalization heuristic
                        cleaned_target = dep.raw_target.lstrip("./")
                        for p, rf in created_files_map.items():
                            if p.startswith(cleaned_target) or os.path.splitext(p)[0] == cleaned_target:
                                target_file_id = rf.id
                                break
                    else:
                        ext_pkg = dep.raw_target

                    code_dep = CodeDependency(
                        id=uuid.uuid4(),
                        source_file_id=source_file_id,
                        target_file_id=target_file_id,
                        external_package=ext_pkg,
                        dependency_type=dep.dependency_type,
                        line_number=dep.line_number,
                    )
                    session.add(code_dep)

                # 6. Finalize Snapshot and Project Status
                snapshot.processed_files = processed_count
                snapshot.status = SnapshotStatus.COMPLETED
                snapshot.completed_at = utc_now()

                # Update Project status to READY
                proj_query = select(Project).where(Project.id == repository.project_id)
                proj_res = await session.execute(proj_query)
                proj = proj_res.scalar_one_or_none()
                if proj:
                    proj.status = ProjectStatus.READY

                await session.commit()
                logger.info(f"Ingestion completed for repository {repository.full_name}, snapshot {snapshot.id}")

            except Exception as e:
                logger.error(f"Ingestion failed for snapshot {snapshot_id}: {e}", exc_info=True)
                snapshot.status = SnapshotStatus.FAILED
                snapshot.error_message = str(e)
                snapshot.completed_at = utc_now()
                await session.commit()
            finally:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
