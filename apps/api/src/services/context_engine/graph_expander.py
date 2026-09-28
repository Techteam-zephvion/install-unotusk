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
        """
        Iteratively expands seed candidates through multi-hop BFS graph traversal.
        Discovers direct and transitive outbound dependencies, inbound callers,
        and defined symbols up to max_depth.
        """
        if not seed_candidates or max_depth < 1:
            return seed_candidates or []

        expanded: dict[str, RetrievedCandidate] = {c.candidate_id: c for c in seed_candidates}
        seed_file_ids = {c.file_id for c in seed_candidates if c.file_id}

        if not seed_file_ids:
            return list(expanded.values())

        SourceFile = aliased(RepositoryFile, name="source_file")
        TargetFile = aliased(RepositoryFile, name="target_file")

        visited_file_ids: set[uuid.UUID] = set(seed_file_ids)
        current_frontier: set[uuid.UUID] = set(seed_file_ids)

        for depth in range(1, max_depth + 1):
            if not current_frontier or len(expanded) >= max_expansions * 4:
                break

            frontier_list = list(current_frontier)
            next_frontier: set[uuid.UUID] = set()

            # Signal key: hop 1 uses 'graph_expansion', hop 2 uses 'graph_expansion_hop2', hop N uses 'graph_expansion_hop{depth}'
            signal_key = "graph_expansion" if depth == 1 else f"graph_expansion_hop{depth}"

            # Decay factor with depth
            sym_weight = max(0.2, round(0.5 * (0.75 ** (depth - 1)), 2))
            dep_weight = max(0.15, round(0.45 * (0.75 ** (depth - 1)), 2))
            file_weight = max(0.15, round(0.4 * (0.75 ** (depth - 1)), 2))

            # 1. Expand Symbols defined in files of the current frontier
            sym_limit = max_expansions if depth == 1 else max(3, max_expansions // depth)
            sym_stmt = (
                select(CodeSymbol, RepositoryFile)
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(CodeSymbol.file_id.in_(frontier_list))
                .limit(sym_limit)
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
                        signals={signal_key: sym_weight},
                    )

            # 2. Expand Dependencies: Outbound & Inbound relationships for current frontier
            dep_limit = max_expansions if depth == 1 else max(3, max_expansions // depth)
            dep_stmt = (
                select(CodeDependency, SourceFile, TargetFile)
                .join(SourceFile, SourceFile.id == CodeDependency.source_file_id)
                .outerjoin(TargetFile, TargetFile.id == CodeDependency.target_file_id)
                .where(
                    or_(
                        CodeDependency.source_file_id.in_(frontier_list),
                        CodeDependency.target_file_id.in_(frontier_list),
                    )
                )
                .limit(dep_limit)
            )
            dep_res = await session.execute(dep_stmt)

            for dep, src_file, tgt_file in dep_res.all():
                cid = f"dep:{dep.id}"
                is_outbound = dep.source_file_id in frontier_list

                if is_outbound:
                    # Outbound dependency: frontier node (src_file) imports target (tgt_file)
                    target_desc = (
                        tgt_file.path if tgt_file else (dep.external_package or "external module")
                    )
                    prefix = (
                        "Outbound Dependency"
                        if depth == 1
                        else f"Transitive Dependency ({depth}-hop)"
                    )
                    content = f"{prefix}: {src_file.path} -> {target_desc} (imports {target_desc}, line {dep.line_number})"
                    dep_name = (
                        tgt_file.filename if tgt_file else (dep.external_package or "dependency")
                    )
                    primary_file = tgt_file if tgt_file else src_file

                    if tgt_file and tgt_file.id not in visited_file_ids:
                        next_frontier.add(tgt_file.id)
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
                                signals={signal_key: file_weight},
                            )
                else:
                    # Inbound dependency: caller (src_file) imports frontier node (tgt_file)
                    target_seed_desc = tgt_file.path if tgt_file else "target module"
                    prefix = (
                        "Inbound Dependency"
                        if depth == 1
                        else f"Inbound Transitive Caller ({depth}-hop)"
                    )
                    content = f"{prefix}: {target_seed_desc} imported by {src_file.path} ({src_file.path} imports {target_seed_desc}, line {dep.line_number})"
                    dep_name = src_file.filename or "caller dependency"
                    primary_file = src_file

                    if src_file.id not in visited_file_ids:
                        next_frontier.add(src_file.id)
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
                                signals={signal_key: file_weight},
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
                        signals={signal_key: dep_weight},
                    )

            visited_file_ids.update(next_frontier)
            current_frontier = next_frontier

        # Fetch code chunks for highest-relevance symbols to supply actual code
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
