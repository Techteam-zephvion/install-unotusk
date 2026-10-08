import os
import uuid
from typing import TYPE_CHECKING

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.code_atom import AtomicCodeChange
from apps.api.src.services.code_atom.embedding import generate_atom_code_embedding

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def generate_deterministic_chunk_id(fingerprint: str) -> uuid.UUID:
    """Generates a stable, reproducible UUID for an atomic code chunk using RFC 4122 v5."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"code-atom:{fingerprint}")


def map_atomic_code_change_to_code_chunk(
    change: AtomicCodeChange,
    snapshot_id: uuid.UUID,
    file_id: uuid.UUID,
    symbol_id: uuid.UUID | None = None,
    compute_embedding: bool = True,
) -> CodeChunk:
    """
    Maps a canonical AtomicCodeChange into an existing CodeChunk model instance.

    Guarantees:
    - Reuses existing CodeChunk schema without divergence.
    - Preserves deterministic fingerprint, parent commit SHA, message, and full provenance.
    - Resolves start/end line bounds appropriately.
    - Generates and populates 1536-dim vector embedding when compute_embedding is True.
    """
    # Calculate line boundaries
    start_line = (
        change.new_start_line
        if change.new_start_line is not None and change.new_start_line > 0
        else (change.old_start_line if change.old_start_line and change.old_start_line > 0 else 1)
    )
    line_count = (
        change.new_line_count
        if change.new_line_count is not None
        else (change.old_line_count if change.old_line_count is not None else 1)
    )
    end_line = max(start_line, start_line + max(0, line_count - 1))

    # Descriptive chunk name
    base_file = os.path.basename(change.file_path)
    if change.symbol_name:
        chunk_name = f"{change.symbol_name} ({change.change_type.value})"
    else:
        chunk_name = f"{base_file} ({change.change_type.value})"

    # Chunk type distinguishing atomic changes
    chunk_type = f"ATOM_{change.change_type.value}"

    # Stable chunk ID
    chunk_id = generate_deterministic_chunk_id(change.fingerprint)

    # Provenance dictionary copy
    prov_data = dict(change.provenance) if change.provenance else {}
    prov_data["atom_id"] = change.id
    prov_data["fingerprint"] = change.fingerprint

    # Generate embedding if requested
    embedding_vec: list[float] | None = None
    if compute_embedding:
        try:
            embedding_vec = generate_atom_code_embedding(
                commit_message=change.commit_message,
                content=change.raw_content,
                file_path=change.file_path,
                symbol_name=change.symbol_name,
            )
        except Exception:
            embedding_vec = None

    return CodeChunk(
        id=chunk_id,
        snapshot_id=snapshot_id,
        file_id=file_id,
        symbol_id=symbol_id if symbol_id is not None else change.symbol_id,
        chunk_type=chunk_type,
        name=chunk_name,
        path=change.file_path,
        content=change.raw_content,
        start_line=start_line,
        end_line=end_line,
        commit_sha=change.commit_sha,
        commit_message=change.commit_message,
        fingerprint=change.fingerprint,
        provenance=prov_data,
        embedding=embedding_vec,
    )


def resolve_and_map_atomic_changes(
    changes: list[AtomicCodeChange],
    snapshot_id: uuid.UUID,
    files_map: dict[str, RepositoryFile],
    symbols_map: dict[str, CodeSymbol] | None = None,
    session: "AsyncSession | None" = None,
    compute_embedding: bool = True,
    existing_chunks_by_fingerprint: dict[str, CodeChunk] | None = None,
) -> list[CodeChunk]:
    """
    Resolves entity links (Snapshot, RepositoryFile, CodeSymbol) and maps AtomicCodeChange units
    into CodeChunk instances.

    Guarantees:
    - Never creates duplicate RepositoryFile entities.
    - If a symbol cannot be resolved, leaves symbol_id=None.
    - Preserves all provenance, fingerprint, and commit context.
    - Computes and populates 1536-dim embeddings when compute_embedding is True.
    - Reuses existing chunks by fingerprint when provided to avoid re-embedding.
    """
    mapped_chunks: list[CodeChunk] = []
    # Build a normalized path lookup map for fast resolution: normalized_path -> RepositoryFile
    norm_files: dict[str, RepositoryFile] = {}
    for p, rf in files_map.items():
        norm_files[p.replace("\\", "/").strip().lstrip("/")] = rf

    for change in changes:
        # Avoid re-embedding or creating duplicate chunks if already present
        if existing_chunks_by_fingerprint and change.fingerprint in existing_chunks_by_fingerprint:
            mapped_chunks.append(existing_chunks_by_fingerprint[change.fingerprint])
            continue

        clean_path = change.file_path.replace("\\", "/").strip().lstrip("/")
        repo_file = norm_files.get(clean_path)

        # If not matched directly, try old_file_path if rename
        if repo_file is None and change.old_file_path:
            clean_old = change.old_file_path.replace("\\", "/").strip().lstrip("/")
            repo_file = norm_files.get(clean_old)

        # If still not found (e.g. deleted file), create a single RepositoryFile representation and register it
        if repo_file is None:
            repo_file = RepositoryFile(
                id=uuid.uuid4(),
                snapshot_id=snapshot_id,
                path=change.file_path,
                filename=os.path.basename(change.file_path),
                extension=os.path.splitext(change.file_path)[1].lower(),
                language="UNKNOWN",
                size_bytes=0,
                content_hash="",
                is_binary=False,
                is_generated=False,
                is_test=False,
                line_count=0,
                parser_supported=False,
            )
            norm_files[clean_path] = repo_file
            files_map[change.file_path] = repo_file
            if session is not None:
                session.add(repo_file)

        # Symbol resolution
        resolved_symbol_id: uuid.UUID | None = change.symbol_id
        if resolved_symbol_id is None and change.symbol_name and symbols_map:
            # Check by composite key file_id:symbol_name or symbol_name
            comp_key = f"{repo_file.id}:{change.symbol_name}"
            sym_match = symbols_map.get(comp_key) or symbols_map.get(change.symbol_name)
            if sym_match:
                resolved_symbol_id = sym_match.id

        chunk = map_atomic_code_change_to_code_chunk(
            change=change,
            snapshot_id=snapshot_id,
            file_id=repo_file.id,
            symbol_id=resolved_symbol_id,
            compute_embedding=compute_embedding,
        )
        mapped_chunks.append(chunk)

    return mapped_chunks
