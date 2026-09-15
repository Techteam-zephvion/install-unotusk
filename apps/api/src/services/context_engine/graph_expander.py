import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


class RelationshipExpander:
    @staticmethod
    async def expand_candidates(
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        seed_candidates: list[RetrievedCandidate],
        max_expansions: int = 10,
    ) -> list[RetrievedCandidate]:
        if not seed_candidates:
            return []

        expanded: dict[str, RetrievedCandidate] = {c.candidate_id: c for c in seed_candidates}
        seed_file_ids = list({c.file_id for c in seed_candidates})

        # 1. Expand from Files: Find symbols defined in those files if not already retrieved
        if seed_file_ids:
            sym_stmt = (
                select(CodeSymbol, RepositoryFile)
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(
                    CodeSymbol.file_id.in_(seed_file_ids[:10]),
                )
                .limit(max_expansions)
            )
            sym_res = await session.execute(sym_stmt)
            for sym, f in sym_res.all():
                cid = f"sym:{sym.id}"
                if cid not in expanded:
                    expanded[cid] = RetrievedCandidate(
                        candidate_id=cid,
                        entity_type="SYMBOL",
                        name=sym.name,
                        path=f.path,
                        start_line=sym.start_line,
                        end_line=sym.end_line,
                        content=f"{sym.symbol_type.value} {sym.qualified_name} (lines {sym.start_line}-{sym.end_line} in {f.path})",
                        file_id=f.id,
                        symbol_id=sym.id,
                        signals={"graph_expansion": 0.5},
                    )

            # 2. Expand Dependencies: Outbound and Inbound dependencies for seed files
            dep_stmt = (
                select(CodeDependency, RepositoryFile)
                .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
                .where(
                    or_(
                        CodeDependency.source_file_id.in_(seed_file_ids[:10]),
                        CodeDependency.target_file_id.in_(seed_file_ids[:10]),
                    )
                )
                .limit(max_expansions)
            )
            dep_res = await session.execute(dep_stmt)
            for dep, src_file in dep_res.all():
                cid = f"dep:{dep.id}"
                if cid not in expanded:
                    expanded[cid] = RetrievedCandidate(
                        candidate_id=cid,
                        entity_type="DEPENDENCY",
                        name=dep.external_package or "dependency",
                        path=src_file.path,
                        start_line=dep.line_number,
                        end_line=dep.line_number,
                        content=f"Dependency: {src_file.path} -> {dep.external_package or 'internal module'} (line {dep.line_number})",
                        file_id=src_file.id,
                        signals={"graph_expansion": 0.45},
                    )

            # 3. Fetch code chunks for highest-relevance symbols/files to supply actual code snippets
            missing_chunk_sym_ids = [
                c.symbol_id for c in expanded.values() if c.symbol_id and c.entity_type == "SYMBOL"
            ]
            if missing_chunk_sym_ids:
                chunk_stmt = select(CodeChunk).where(
                    CodeChunk.snapshot_id == snapshot_id,
                    CodeChunk.symbol_id.in_(missing_chunk_sym_ids[:10]),
                )
                chunk_res = await session.execute(chunk_stmt)
                for chunk in chunk_res.scalars().all():
                    # Upgrade the symbol candidate's content to full code snippet if available
                    sym_cid = f"sym:{chunk.symbol_id}"
                    if sym_cid in expanded:
                        expanded[sym_cid].content = chunk.content

        return list(expanded.values())
