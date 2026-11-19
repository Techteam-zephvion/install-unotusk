from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol


class RepositorySkeletonBuilder:
    """
    Constructs a comprehensive, high-density architectural skeleton of the indexed repository snapshot.
    This provides the LLM with global macro-level awareness of:
      1. Primary Frameworks, Languages & Package Manifests
      2. Architectural Tiers (Presentation / UI, API Routing, Domain Logic, Persistence, Infrastructure)
      3. Entry Points & Core Directory Topologies
      4. Key Classes, Entities, and Interfaces
    """

    @classmethod
    async def build_skeleton(
        cls,
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        max_symbols_per_tier: int = 8,
    ) -> str:
        # 1. Fetch file inventory grouped by directory
        file_stmt = (
            select(RepositoryFile.path, RepositoryFile.filename, RepositoryFile.language)
            .where(RepositoryFile.snapshot_id == snapshot_id)
            .order_by(RepositoryFile.path.asc())
        )
        file_res = await session.execute(file_stmt)
        all_files = file_res.all()

        if not all_files:
            return ""

        # Analyze directory topologies & frameworks
        dir_counts: dict[str, int] = {}
        manifests: list[str] = []
        entry_points: list[str] = []
        detected_languages: set[str] = set()

        entry_candidates = {
            "main.dart",
            "main.py",
            "app.py",
            "server.py",
            "index.ts",
            "index.js",
            "app.tsx",
            "main.go",
            "server.go",
            "main.rs",
            "docker-compose.yml",
            "docker-compose.yaml",
        }

        manifest_candidates = {
            "pubspec.yaml",
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "go.mod",
            "cargo.toml",
            "pom.xml",
            "build.gradle",
        }

        for path, filename, lang in all_files:
            if lang:
                detected_languages.add(lang.lower())
            fn_low = filename.lower()
            if fn_low in entry_candidates:
                entry_points.append(path)
            if fn_low in manifest_candidates:
                manifests.append(path)

            parts = path.split("/")
            if len(parts) > 1:
                top_dir = parts[0] if parts[0] else parts[1]
                if len(parts) > 2 and top_dir in ("src", "apps", "lib", "packages"):
                    top_dir = f"{top_dir}/{parts[1]}"
                dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1
            else:
                dir_counts["<root>"] = dir_counts.get("<root>", 0) + 1

        # 2. Fetch external dependencies
        dep_stmt = (
            select(CodeDependency.external_package)
            .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
            .where(
                RepositoryFile.snapshot_id == snapshot_id,
                CodeDependency.external_package.isnot(None),
            )
            .distinct()
            .limit(16)
        )
        dep_res = await session.execute(dep_stmt)
        external_deps = [d for d in dep_res.scalars().all() if d]

        # 3. Categorize Code Symbols into Architectural Tiers
        sym_stmt = (
            select(CodeSymbol.name, CodeSymbol.qualified_name, CodeSymbol.symbol_type, RepositoryFile.path)
            .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
            .where(
                RepositoryFile.snapshot_id == snapshot_id,
            )
            .order_by(CodeSymbol.name.asc())
            .limit(200)
        )
        sym_res = await session.execute(sym_stmt)
        all_symbols = sym_res.all()

        ui_symbols: list[str] = []
        api_symbols: list[str] = []
        domain_symbols: list[str] = []
        data_symbols: list[str] = []
        infra_symbols: list[str] = []

        for name, qname, _stype, fpath in all_symbols:
            low = f"{name} {qname} {fpath}".lower()
            ref_str = f"`{name}` ({fpath})"

            if any(k in low for k in ("screen", "view", "page", "widget", "component", "button", "dialog", "tab", "ui/")):
                if len(ui_symbols) < max_symbols_per_tier and ref_str not in ui_symbols:
                    ui_symbols.append(ref_str)
            elif any(k in low for k in ("router", "route", "endpoint", "controller", "handler", "api/", "routes/")):
                if len(api_symbols) < max_symbols_per_tier and ref_str not in api_symbols:
                    api_symbols.append(ref_str)
            elif any(k in low for k in ("model", "schema", "entity", "table", "repository", "db/", "store/", "database")):
                if len(data_symbols) < max_symbols_per_tier and ref_str not in data_symbols:
                    data_symbols.append(ref_str)
            elif any(k in low for k in ("worker", "task", "queue", "redis", "client", "service", "job", "pipeline", "cache")):
                if len(infra_symbols) < max_symbols_per_tier and ref_str not in infra_symbols:
                    infra_symbols.append(ref_str)
            else:
                if len(domain_symbols) < max_symbols_per_tier and ref_str not in domain_symbols:
                    domain_symbols.append(ref_str)

        # 4. Format Structured Output
        lines: list[str] = [
            "## REPOSITORY GLOBAL ARCHITECTURAL SKELETON & TOPOLOGY",
            f"- **Detected Stacks / Languages**: {', '.join(sorted(detected_languages)) or 'Mixed'}",
            f"- **Key Manifests & Configs**: {', '.join(manifests) if manifests else 'None explicitly indexed'}",
            f"- **Primary Entrypoints**: {', '.join(entry_points) if entry_points else 'Discovered via package topology'}",
        ]

        if external_deps:
            lines.append(f"- **Key Frameworks / Dependencies**: {', '.join(external_deps[:12])}")

        # Directory Map
        top_dirs_sorted = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        dir_summary = [f"`{d}/` ({cnt} files)" for d, cnt in top_dirs_sorted]
        lines.append(f"- **Major Code Directories**: {', '.join(dir_summary)}")

        lines.append("\n### Verified Component Tiers (Grounding Entities for Architecture Diagrams):")
        if ui_symbols:
            lines.append(f"- **UI / Presentation Layer**: {', '.join(ui_symbols)}")
        if api_symbols:
            lines.append(f"- **API / Routing / Controllers**: {', '.join(api_symbols)}")
        if domain_symbols:
            lines.append(f"- **Domain Services & Logic**: {', '.join(domain_symbols)}")
        if data_symbols:
            lines.append(f"- **Data Models & Persistence**: {', '.join(data_symbols)}")
        if infra_symbols:
            lines.append(f"- **Workers & Infrastructure**: {', '.join(infra_symbols)}")

        lines.append(
            "\n*When synthesizing architectural descriptions or Mermaid diagrams, prioritize the above actual components across their real tiers.*"
        )

        return "\n".join(lines)
