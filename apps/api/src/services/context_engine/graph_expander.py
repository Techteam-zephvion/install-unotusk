import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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
        max_depth: int = 2,
    ) -> list[RetrievedCandidate]:
        if not seed_candidates:
            return []

        expanded: dict[str, RetrievedCandidate] = {c.candidate_id: c for c in seed_candidates}
        seed_file_ids = list({c.file_id for c in seed_candidates})

        if not seed_file_ids:
            return list(expanded.values())

        # =========================================================================
        # HOP 1: Expand direct symbols, outbound dependencies, and inbound callers
        # =========================================================================
        # 1. Expand from Files: Find symbols defined in those files
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
        # Join BOTH SourceFile and TargetFile to correctly resolve inbound and outbound records
        SourceFile = aliased(RepositoryFile, name="source_file")
        TargetFile = aliased(RepositoryFile, name="target_file")

        dep_stmt = (
            select(CodeDependency, SourceFile, TargetFile)
            .join(SourceFile, SourceFile.id == CodeDependency.source_file_id)
            .outerjoin(TargetFile, TargetFile.id == CodeDependency.target_file_id)
            .where(
                or_(
                    CodeDependency.source_file_id.in_(seed_file_ids[:10]),
                    CodeDependency.target_file_id.in_(seed_file_ids[:10]),
                )
            )
            .limit(max_expansions)
        )
        dep_res = await session.execute(dep_stmt)

        hop1_connected_file_ids: set[uuid.UUID] = set()

        for dep, src_file, tgt_file in dep_res.all():
            cid = f"dep:{dep.id}"
            is_outbound = dep.source_file_id in seed_file_ids[:10]

            if is_outbound:
                target_desc = tgt_file.path if tgt_file else (dep.external_package or "external module")
                content = f"Outbound Dependency: {src_file.path} -> {target_desc} (line {dep.line_number})"
                dep_name = tgt_file.filename if tgt_file else (dep.external_package or "dependency")
                primary_file = src_file
                if tgt_file and tgt_file.id not in seed_file_ids:
                    hop1_connected_file_ids.add(tgt_file.id)
                    fcid = f"file:{tgt_file.id}"
                    if fcid not in expanded:
                        expanded[fcid] = RetrievedCandidate(
                            candidate_id=fcid,
                            entity_type="FILE",
                            name=tgt_file.filename,
                            path=tgt_file.path,
                            start_line=1,
                            end_line=tgt_file.line_count or 1,
                            content=f"// Connected Target File: {tgt_file.path} ({tgt_file.language or 'text'}, {tgt_file.line_count} lines)",
                            file_id=tgt_file.id,
                            signals={"graph_expansion": 0.4},
                        )
            else:
                # Inbound dependency: src_file imports the seed file (tgt_file)
                target_seed_desc = tgt_file.path if tgt_file else "seed module"
                content = f"Inbound Dependency: {src_file.path} imports {target_seed_desc} (line {dep.line_number})"
                dep_name = src_file.filename or "caller dependency"
                primary_file = src_file
                if src_file.id not in seed_file_ids:
                    hop1_connected_file_ids.add(src_file.id)
                    fcid = f"file:{src_file.id}"
                    if fcid not in expanded:
                        expanded[fcid] = RetrievedCandidate(
                            candidate_id=fcid,
                            entity_type="FILE",
                            name=src_file.filename,
                            path=src_file.path,
                            start_line=1,
                            end_line=src_file.line_count or 1,
                            content=f"// Connected Caller File: {src_file.path} ({src_file.language or 'text'}, {src_file.line_count} lines)",
                            file_id=src_file.id,
                            signals={"graph_expansion": 0.4},
                        )

            if cid not in expanded:
                expanded[cid] = RetrievedCandidate(
                    candidate_id=cid,
                    entity_type="DEPENDENCY",
                    name=dep_name,
                    path=primary_file.path,
                    start_line=dep.line_number,
                    end_line=dep.line_number,
                    content=content,
                    file_id=primary_file.id,
                    signals={"graph_expansion": 0.45},
                )

        # =========================================================================
        # HOP 2: Multi-hop graph traversal for transitive dependencies and symbols
        # =========================================================================
        if max_depth >= 2 and hop1_connected_file_ids:
            hop1_ids_list = list(hop1_connected_file_ids)[:5]

            # Hop 2 Symbols: Key symbols in connected files
            hop2_sym_stmt = (
                select(CodeSymbol, RepositoryFile)
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(
                    CodeSymbol.file_id.in_(hop1_ids_list),
                )
                .limit(max(3, max_expansions // 2))
            )
            hop2_sym_res = await session.execute(hop2_sym_stmt)
            for sym, f in hop2_sym_res.all():
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
                        signals={"graph_expansion_hop2": 0.35},
                    )

            # Hop 2 Dependencies: Transitive dependencies of connected files
            hop2_dep_stmt = (
                select(CodeDependency, SourceFile, TargetFile)
                .join(SourceFile, SourceFile.id == CodeDependency.source_file_id)
                .outerjoin(TargetFile, TargetFile.id == CodeDependency.target_file_id)
                .where(
                    CodeDependency.source_file_id.in_(hop1_ids_list),
                )
                .limit(max(3, max_expansions // 2))
            )
            hop2_dep_res = await session.execute(hop2_dep_stmt)
            for dep, src_file, tgt_file in hop2_dep_res.all():
                cid = f"dep:{dep.id}"
                if cid not in expanded:
                    target_desc = tgt_file.path if tgt_file else (dep.external_package or "external module")
                    expanded[cid] = RetrievedCandidate(
                        candidate_id=cid,
                        entity_type="DEPENDENCY",
                        name=tgt_file.filename if tgt_file else (dep.external_package or "dependency"),
                        path=src_file.path,
                        start_line=dep.line_number,
                        end_line=dep.line_number,
                        content=f"Transitive Dependency (2-hop): {src_file.path} -> {target_desc} (line {dep.line_number})",
                        file_id=src_file.id,
                        signals={"graph_expansion_hop2": 0.3},
                    )

        # =========================================================================
        # 3. Fetch code chunks for highest-relevance symbols to supply actual code
        # =========================================================================
        missing_chunk_sym_ids = [
            c.symbol_id for c in expanded.values() if c.symbol_id and c.entity_type == "SYMBOL"
        ]
        if missing_chunk_sym_ids:
            chunk_stmt = select(CodeChunk).where(
                CodeChunk.snapshot_id == snapshot_id,
                CodeChunk.symbol_id.in_(missing_chunk_sym_ids[:15]),
            )
            chunk_res = await session.execute(chunk_stmt)
            for chunk in chunk_res.scalars().all():
                sym_cid = f"sym:{chunk.symbol_id}"
                if sym_cid in expanded:
                    expanded[sym_cid].content = chunk.content

        return list(expanded.values())
