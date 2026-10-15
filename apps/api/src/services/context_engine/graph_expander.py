import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.context_engine.retriever import (
    RetrievedCandidate,
    _extract_chunk_metadata,
)


class RelationshipExpander:
    @staticmethod
    def _record_relationship_provenance(
        existing: RetrievedCandidate,
        new_hop: int,
        new_path: str,
        new_type: str,
        connected_from: str,
        retrieval_reason: str,
        signal_key: str,
        signal_weight: float,
    ) -> None:
        """Deduplicates multiple paths to the same candidate while preserving provenance."""
        exist_hop = existing.metadata.get("relationship_hop", new_hop)
        exist_path = existing.metadata.get("relationship_path")

        if new_hop < exist_hop:
            # Shorter path found: adopt new hop and path, archive old path in alternative_paths
            if exist_path and exist_path != new_path:
                alt_list = existing.metadata.setdefault("alternative_paths", [])
                if exist_path not in alt_list:
                    alt_list.append(exist_path)
            existing.metadata["relationship_hop"] = new_hop
            existing.metadata["relationship_path"] = new_path
            existing.metadata["relationship_type"] = new_type
            existing.metadata["connected_from"] = connected_from
            existing.metadata["retrieval_reason"] = retrieval_reason
        else:
            # Same or longer path: archive new path in alternative_paths
            if new_path and new_path != exist_path:
                alt_list = existing.metadata.setdefault("alternative_paths", [])
                if new_path not in alt_list:
                    alt_list.append(new_path)

        existing.signals[signal_key] = max(existing.signals.get(signal_key, 0.0), signal_weight)

    @staticmethod
    async def expand_candidates(
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        seed_candidates: list[RetrievedCandidate],
        max_expansions: int = 10,
        max_depth: int = 2,
    ) -> list[RetrievedCandidate]:
        """Iteratively expands seed candidates through multi-hop BFS graph traversal.
        Discovers direct and transitive outbound dependencies, inbound callers,
        and defined symbols up to max_depth.
        """
        if not seed_candidates or max_depth < 1:
            return seed_candidates or []

        # Annotate seed candidates with baseline relationship provenance
        for c in seed_candidates:
            if "is_seed" not in c.metadata:
                c.metadata["is_seed"] = True
            if "relationship_hop" not in c.metadata:
                c.metadata["relationship_hop"] = 0
            if "retrieval_reason" not in c.metadata:
                c.metadata["retrieval_reason"] = "Direct retrieval match"

        expanded: dict[str, RetrievedCandidate] = {c.candidate_id: c for c in seed_candidates}

        # Expand grounded temporal relations present in seed candidate metadata
        for c in seed_candidates:
            rels = c.metadata.get("temporal_relations")
            if isinstance(rels, list) and rels:
                for rel in rels:
                    if isinstance(rel, dict):
                        target_str = rel.get("canonical_object") or rel.get("object")
                        rel_type = rel.get("relation", "CALLS")
                        is_ended = bool(rel.get("t_end"))
                        if target_str:
                            rel_cid = f"temporal_rel:{target_str}"
                            if rel_cid not in expanded and len(expanded) < max_expansions * 4:
                                target_path = target_str.split("::")[0] if "::" in target_str else c.path
                                sym_name = target_str.split("::")[-1] if "::" in target_str else target_str
                                rel_path = f"{c.path} -> {str(rel_type).lower()} -> {target_str}"
                                reason = (
                                    f"Historical ended relation: {c.name} {rel_type} {target_str}"
                                    if is_ended
                                    else f"Verified temporal relation: {c.name} {rel_type} {target_str}"
                                )
                                expanded[rel_cid] = RetrievedCandidate(
                                    candidate_id=rel_cid,
                                    entity_type="RELATION_TARGET",
                                    name=sym_name,
                                    path=target_path,
                                    start_line=1,
                                    end_line=1,
                                    content=f"// Resolved Temporal Relation Target: ({c.name} {rel_type} {target_str})",
                                    file_id=c.file_id,
                                    signals={"graph_expansion": 0.45},
                                    metadata={
                                        "relationship_path": rel_path,
                                        "relationship_type": str(rel_type),
                                        "relationship_hop": 1,
                                        "connected_from": c.path,
                                        "retrieval_reason": reason,
                                        "alternative_paths": [],
                                        "is_ended_relation": is_ended,
                                        "temporal_relations": [rel],
                                    },
                                )

        seed_file_ids = {c.file_id for c in seed_candidates if c.file_id}

        if not seed_file_ids:
            return list(expanded.values())

        SourceFile = aliased(RepositoryFile, name="source_file")
        TargetFile = aliased(RepositoryFile, name="target_file")

        # Source map tracks human-readable names and candidate IDs for provenance
        source_map: dict[uuid.UUID, tuple[str, str]] = {}
        for c in seed_candidates:
            if c.file_id:
                source_map[c.file_id] = (c.path or c.name, c.candidate_id)
            if c.symbol_id:
                source_map[c.symbol_id] = (c.name, c.candidate_id)

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
                src_name, _ = source_map.get(f.id, (f.filename or f.path, f"file:{f.id}"))
                rel_path = f"{src_name} -> defines -> {sym.name}"
                rel_reason = f"Defined symbol in connected file {f.filename} (hop {depth})"

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
                        metadata={
                            "relationship_path": rel_path,
                            "relationship_type": "REFERENCED_SYMBOL",
                            "relationship_hop": depth,
                            "connected_from": src_name,
                            "retrieval_reason": rel_reason,
                            "alternative_paths": [],
                        },
                    )
                else:
                    RelationshipExpander._record_relationship_provenance(
                        existing=expanded[cid],
                        new_hop=depth,
                        new_path=rel_path,
                        new_type="REFERENCED_SYMBOL",
                        connected_from=src_name,
                        retrieval_reason=rel_reason,
                        signal_key=signal_key,
                        signal_weight=sym_weight,
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
                    rel_type = "CALLEE"
                    dep_rel_path = f"{src_file.path} -> imports -> {target_desc}"
                    connected_from = src_file.filename or src_file.path
                    dep_reason = f"Connected callee dependency (hop {depth}) from {connected_from}"

                    if tgt_file and tgt_file.id not in visited_file_ids:
                        next_frontier.add(tgt_file.id)
                        source_map[tgt_file.id] = (tgt_file.path, f"file:{tgt_file.id}")
                        fcid = f"file:{tgt_file.id}"
                        file_rel_path = f"{src_file.path} -> imports -> {tgt_file.path}"
                        file_reason = f"Connected target file (hop {depth}) imported by {connected_from}"
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
                                metadata={
                                    "relationship_path": file_rel_path,
                                    "relationship_type": "CALLEE",
                                    "relationship_hop": depth,
                                    "connected_from": connected_from,
                                    "retrieval_reason": file_reason,
                                    "alternative_paths": [],
                                },
                            )
                        else:
                            RelationshipExpander._record_relationship_provenance(
                                existing=expanded[fcid],
                                new_hop=depth,
                                new_path=file_rel_path,
                                new_type="CALLEE",
                                connected_from=connected_from,
                                retrieval_reason=file_reason,
                                signal_key=signal_key,
                                signal_weight=file_weight,
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
                    rel_type = "CALLER"
                    dep_rel_path = f"{src_file.path} -> calls -> {target_seed_desc}"
                    connected_from = target_seed_desc
                    dep_reason = f"Connected inbound caller (hop {depth}) calling {target_seed_desc}"

                    if src_file.id not in visited_file_ids:
                        next_frontier.add(src_file.id)
                        source_map[src_file.id] = (src_file.path, f"file:{src_file.id}")
                        fcid = f"file:{src_file.id}"
                        file_rel_path = f"{src_file.path} -> calls -> {target_seed_desc}"
                        file_reason = f"Connected caller file (hop {depth}) calling {target_seed_desc}"
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
                                metadata={
                                    "relationship_path": file_rel_path,
                                    "relationship_type": "CALLER",
                                    "relationship_hop": depth,
                                    "connected_from": connected_from,
                                    "retrieval_reason": file_reason,
                                    "alternative_paths": [],
                                },
                            )
                        else:
                            RelationshipExpander._record_relationship_provenance(
                                existing=expanded[fcid],
                                new_hop=depth,
                                new_path=file_rel_path,
                                new_type="CALLER",
                                connected_from=connected_from,
                                retrieval_reason=file_reason,
                                signal_key=signal_key,
                                signal_weight=file_weight,
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
                        metadata={
                            "relationship_path": dep_rel_path,
                            "relationship_type": rel_type,
                            "relationship_hop": depth,
                            "connected_from": connected_from,
                            "retrieval_reason": dep_reason,
                            "alternative_paths": [],
                        },
                    )
                else:
                    RelationshipExpander._record_relationship_provenance(
                        existing=expanded[cid],
                        new_hop=depth,
                        new_path=dep_rel_path,
                        new_type=rel_type,
                        connected_from=connected_from,
                        retrieval_reason=dep_reason,
                        signal_key=signal_key,
                        signal_weight=dep_weight,
                    )

            visited_file_ids.update(next_frontier)
            current_frontier = next_frontier

        # Fetch code chunks for highest-relevance symbols and connected files to supply actual code
        missing_chunk_sym_ids = [
            c.symbol_id for c in expanded.values() if c.symbol_id and c.entity_type == "SYMBOL"
        ]
        connected_file_ids = [
            c.file_id for c in expanded.values() if c.file_id and c.file_id not in seed_file_ids
        ]

        if missing_chunk_sym_ids or connected_file_ids:
            chunk_conditions = []
            if missing_chunk_sym_ids:
                chunk_conditions.append(CodeChunk.symbol_id.in_(missing_chunk_sym_ids[:15]))
            if connected_file_ids:
                chunk_conditions.append(CodeChunk.file_id.in_(connected_file_ids[:10]))

            chunk_stmt = select(CodeChunk).where(
                CodeChunk.snapshot_id == snapshot_id,
                or_(*chunk_conditions),
            )
            chunk_res = await session.execute(chunk_stmt)
            for chunk in chunk_res.scalars().all():
                sym_cid = f"sym:{chunk.symbol_id}" if chunk.symbol_id else None
                if sym_cid and sym_cid in expanded:
                    expanded[sym_cid].content = chunk.content
                    for k, v in _extract_chunk_metadata(chunk).items():
                        if k not in expanded[sym_cid].metadata:
                            expanded[sym_cid].metadata[k] = v

                # Register concrete CodeChunk candidate if not already present
                chunk_cid = f"chunk:{chunk.id}"
                atom_cid = f"chunk:atom:{chunk.fingerprint}" if chunk.fingerprint else None
                existing_cand = expanded.get(chunk_cid) or (expanded.get(atom_cid) if atom_cid else None)

                parent_cand = None
                if sym_cid and sym_cid in expanded:
                    parent_cand = expanded[sym_cid]
                elif f"file:{chunk.file_id}" in expanded:
                    parent_cand = expanded[f"file:{chunk.file_id}"]

                rel_hop = parent_cand.metadata.get("relationship_hop", 1) if parent_cand else 1
                rel_type = (
                    parent_cand.metadata.get("relationship_type", "CONNECTED_CHUNK")
                    if parent_cand
                    else "CONNECTED_CHUNK"
                )
                rel_path = (
                    parent_cand.metadata.get("relationship_path", f"{chunk.path} -> {chunk.name}")
                    if parent_cand
                    else f"{chunk.path} -> {chunk.name}"
                )
                conn_from = (
                    parent_cand.metadata.get("connected_from", chunk.path)
                    if parent_cand
                    else chunk.path
                )
                rel_reason = (
                    parent_cand.metadata.get(
                        "retrieval_reason", f"Connected code chunk (hop {rel_hop})"
                    )
                    if parent_cand
                    else f"Connected code chunk (hop {rel_hop})"
                )
                alt_paths = (
                    list(parent_cand.metadata.get("alternative_paths", []))
                    if parent_cand
                    else []
                )

                c_sig_key = "graph_expansion" if rel_hop == 1 else f"graph_expansion_hop{rel_hop}"
                c_weight = max(0.2, round(0.5 * (0.75 ** (rel_hop - 1)), 2))

                if existing_cand is None:
                    meta = _extract_chunk_metadata(chunk)
                    meta.update(
                        {
                            "relationship_path": rel_path,
                            "relationship_type": rel_type,
                            "relationship_hop": rel_hop,
                            "connected_from": conn_from,
                            "retrieval_reason": rel_reason,
                            "alternative_paths": alt_paths,
                        }
                    )
                    expanded[chunk_cid] = RetrievedCandidate(
                        candidate_id=chunk_cid,
                        entity_type="CHUNK",
                        name=chunk.name,
                        path=chunk.path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        file_id=chunk.file_id,
                        symbol_id=chunk.symbol_id,
                        signals={c_sig_key: c_weight},
                        metadata=meta,
                    )
                else:
                    RelationshipExpander._record_relationship_provenance(
                        existing=existing_cand,
                        new_hop=rel_hop,
                        new_path=rel_path,
                        new_type=rel_type,
                        connected_from=conn_from,
                        retrieval_reason=rel_reason,
                        signal_key=c_sig_key,
                        signal_weight=c_weight,
                    )

        return list(expanded.values())
