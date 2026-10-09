import hashlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery


def compute_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def generate_text_embedding(text: str, dim: int = 1536) -> list[float]:
    """Generates a deterministic normalized semantic embedding vector for code or text."""
    if not text or not text.strip():
        return [0.0] * dim

    vec = [0.0] * dim
    tokens = re.findall(r"[A-Za-z0-9_]+|[^\s\w]", text.lower())
    if not tokens:
        return [0.0] * dim

    for token in tokens:
        if len(token) < 2:
            continue
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 1) & 1 else -1.0
        vec[idx] += sign * (1.5 if len(token) > 3 else 1.0)

        subwords = token.split("_")
        if len(subwords) > 1:
            for sw in subwords:
                if len(sw) >= 2:
                    h_sw = int(hashlib.md5(sw.encode("utf-8")).hexdigest(), 16)
                    idx_sw = h_sw % dim
                    sign_sw = 1.0 if (h_sw >> 1) & 1 else -1.0
                    vec[idx_sw] += sign_sw * 0.8

    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0.0:
        return [0.0] * dim
    return [round(x / norm, 6) for x in vec]


@dataclass
class RetrievedCandidate:
    candidate_id: str
    entity_type: str  # "FILE", "SYMBOL", "CHUNK", "DEPENDENCY"
    name: str
    path: str
    start_line: int
    end_line: int
    content: str
    file_id: uuid.UUID
    symbol_id: uuid.UUID | None = None
    signals: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _extract_chunk_metadata(chunk: CodeChunk) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if getattr(chunk, "snapshot_id", None):
        meta["snapshot_id"] = str(chunk.snapshot_id)
    if getattr(chunk, "commit_sha", None):
        meta["commit_sha"] = chunk.commit_sha
    if getattr(chunk, "commit_message", None):
        meta["commit_message"] = chunk.commit_message
    if getattr(chunk, "fingerprint", None):
        meta["fingerprint"] = chunk.fingerprint
    if getattr(chunk, "provenance", None):
        meta["provenance"] = chunk.provenance
    if getattr(chunk, "chunk_type", None):
        meta["chunk_type"] = chunk.chunk_type
    return meta


DEFINITION_PATTERN = re.compile(
    r"""^\s*(?:def\s+|class\s+|function\s+|fn\s+|export\s+(?:default\s+)?(?:class|function|const|let|var|type|interface)\s+|type\s+|interface\s+|pub\s+(?:fn|struct|enum|trait)\s+)""",
    re.MULTILINE,
)


def _check_definition_match(content: str, term: str) -> bool:
    """Checks if term appears in a definition line rather than a comment or string."""
    term_lower = term.lower()
    for line in content.splitlines():
        if term_lower in line.lower() and DEFINITION_PATTERN.search(line):
            return True
    return False


class MultiSignalRetriever:
    @staticmethod
    async def retrieve_candidates(
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        analyzed_query: AnalyzedQuery,
        limit_per_signal: int = 15,
        query_embedding: list[float] | None = None,
    ) -> list[RetrievedCandidate]:
        candidates: dict[str, RetrievedCandidate] = {}

        # 1. FILE SEARCH: Match paths & filenames with exact / prefix / substring differentiation
        file_conditions = []
        for p in analyzed_query.path_candidates:
            file_conditions.append(RepositoryFile.path.ilike(f"%{p}%"))
        for kw in analyzed_query.keywords:
            file_conditions.append(RepositoryFile.filename.ilike(f"%{kw}%"))
            file_conditions.append(RepositoryFile.path.ilike(f"%{kw}%"))

        if file_conditions:
            file_stmt = (
                select(RepositoryFile)
                .where(
                    RepositoryFile.snapshot_id == snapshot_id,
                    or_(*file_conditions),
                )
                .limit(limit_per_signal)
            )
            file_res = await session.execute(file_stmt)
            matched_files = file_res.scalars().all()
            for f in matched_files:
                cid = f"file:{f.id}"
                fn_lower = f.filename.lower()
                fn_stem = fn_lower.rsplit(".", 1)[0]
                path_lower = f.path.lower()

                # Differentiate exact filename match vs prefix match vs substring
                is_exact = any(
                    kw.lower() in (fn_lower, fn_stem) for kw in analyzed_query.keywords
                ) or any(p.lower() == path_lower for p in analyzed_query.path_candidates)
                is_prefix = any(
                    fn_lower.startswith(kw.lower()) for kw in analyzed_query.keywords
                ) or any(path_lower.startswith(p.lower()) for p in analyzed_query.path_candidates)

                if is_exact:
                    score = 1.5
                elif is_prefix:
                    score = 1.2
                else:
                    score = 0.8

                candidates[cid] = RetrievedCandidate(
                    candidate_id=cid,
                    entity_type="FILE",
                    name=f.filename,
                    path=f.path,
                    start_line=1,
                    end_line=f.line_count or 1,
                    content=f"// File: {f.path} ({f.language or 'text'}, {f.line_count} lines)",
                    file_id=f.id,
                    signals={"file_match": score},
                )

        # 2. SYMBOL SEARCH: Match symbol names with exact / prefix / substring differentiation
        symbol_conditions = []
        for sym in analyzed_query.symbol_candidates:
            symbol_conditions.append(CodeSymbol.name.ilike(sym))
            symbol_conditions.append(CodeSymbol.qualified_name.ilike(f"%{sym}%"))
        for kw in analyzed_query.keywords:
            if len(kw) >= 3:
                symbol_conditions.append(CodeSymbol.name.ilike(f"%{kw}%"))
        for p in analyzed_query.path_candidates:
            symbol_conditions.append(RepositoryFile.path.ilike(f"%{p}%"))

        if symbol_conditions:
            sym_stmt = (
                select(CodeSymbol, RepositoryFile)
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(
                    RepositoryFile.snapshot_id == snapshot_id,
                    or_(*symbol_conditions),
                )
                .limit(limit_per_signal)
            )
            sym_res = await session.execute(sym_stmt)
            for sym, f in sym_res.all():
                cid = f"sym:{sym.id}"
                sym_lower = sym.name.lower()

                # Differentiate exact symbol match vs prefix vs qualified substring
                exact_sym = any(
                    s.lower() == sym_lower for s in analyzed_query.symbol_candidates
                ) or any(kw.lower() == sym_lower for kw in analyzed_query.keywords)
                prefix_sym = any(
                    sym_lower.startswith(s.lower()) for s in analyzed_query.symbol_candidates
                ) or any(sym_lower.startswith(kw.lower()) for kw in analyzed_query.keywords)

                if exact_sym:
                    score = 1.6
                elif prefix_sym:
                    score = 1.2
                else:
                    score = 0.8

                candidates[cid] = RetrievedCandidate(
                    candidate_id=cid,
                    entity_type="SYMBOL",
                    name=sym.name,
                    path=f.path,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    content=f"{sym.symbol_type.value} {sym.qualified_name} (lines {sym.start_line}-{sym.end_line} in {f.path})",
                    file_id=f.id,
                    symbol_id=sym.id,
                    signals={"symbol_match": score},
                )

        # 3. CONTENT / CODE CHUNK SEARCH: Match chunk name, path, commit message, and content with definition weighting
        chunk_conditions = []
        for kw in analyzed_query.keywords:
            if len(kw) >= 3:
                chunk_conditions.append(CodeChunk.name.ilike(f"%{kw}%"))
                chunk_conditions.append(CodeChunk.path.ilike(f"%{kw}%"))
                chunk_conditions.append(CodeChunk.content.ilike(f"%{kw}%"))
                chunk_conditions.append(CodeChunk.commit_message.ilike(f"%{kw}%"))
            if len(kw) >= 7:
                chunk_conditions.append(CodeChunk.commit_sha.ilike(f"{kw}%"))
                chunk_conditions.append(CodeChunk.fingerprint.ilike(f"{kw}%"))
        for sym in analyzed_query.symbol_candidates:
            chunk_conditions.append(CodeChunk.name.ilike(f"%{sym}%"))
            chunk_conditions.append(CodeChunk.content.ilike(f"%{sym}%"))
            chunk_conditions.append(CodeChunk.commit_message.ilike(f"%{sym}%"))
        for p in analyzed_query.path_candidates:
            chunk_conditions.append(CodeChunk.path.ilike(f"%{p}%"))

        if chunk_conditions:
            chunk_stmt = (
                select(CodeChunk)
                .where(
                    CodeChunk.snapshot_id == snapshot_id,
                    or_(*chunk_conditions),
                )
                .limit(limit_per_signal)
            )
            chunk_res = await session.execute(chunk_stmt)
            for chunk in chunk_res.scalars().all():
                cid = f"chunk:{chunk.id}"
                cname_lower = chunk.name.lower()
                cname_stem = cname_lower.split(" (")[0].strip()
                cpath_lower = chunk.path.lower()
                cm_lower = (chunk.commit_message or "").lower()

                # Determine lexical match quality:
                # 1. Exact match on chunk definition name or stem (e.g. UserService (ADD) -> UserService)
                # 2. Definition line match in content (e.g. def foo, class Bar)
                # 3. Path / filename match
                # 4. Commit message match
                # 5. Standard content / comment match
                exact_name = any(
                    kw.lower() in (cname_lower, cname_stem) for kw in analyzed_query.keywords
                ) or any(
                    sym.lower() in (cname_lower, cname_stem)
                    for sym in analyzed_query.symbol_candidates
                )

                def_match = any(
                    _check_definition_match(chunk.content, kw) for kw in analyzed_query.keywords
                ) or any(
                    _check_definition_match(chunk.content, sym)
                    for sym in analyzed_query.symbol_candidates
                )

                path_match = any(
                    p.lower() in cpath_lower for p in analyzed_query.path_candidates
                ) or any(kw.lower() in cpath_lower for kw in analyzed_query.keywords)

                commit_match = any(
                    kw.lower() in cm_lower for kw in analyzed_query.keywords if len(kw) >= 3
                ) or any(sym.lower() in cm_lower for sym in analyzed_query.symbol_candidates)

                if exact_name:
                    content_score = 1.4
                elif def_match:
                    content_score = 1.2
                elif path_match:
                    content_score = 1.0
                elif commit_match:
                    content_score = 0.95
                else:
                    content_score = 0.6

                chunk_meta = _extract_chunk_metadata(chunk)
                if cid in candidates:
                    candidates[cid].signals["content_match"] = max(
                        candidates[cid].signals.get("content_match", 0.0), content_score
                    )
                    if chunk_meta:
                        candidates[cid].metadata.update(chunk_meta)
                else:
                    candidates[cid] = RetrievedCandidate(
                        candidate_id=cid,
                        entity_type="CHUNK",
                        name=chunk.name,
                        path=chunk.path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        file_id=chunk.file_id,
                        symbol_id=chunk.symbol_id,
                        signals={"content_match": content_score},
                        metadata=chunk_meta,
                    )

        # 4. DEPENDENCY SEARCH: Match packages and imported modules
        dep_conditions = []
        for kw in analyzed_query.keywords:
            if len(kw) >= 3:
                dep_conditions.append(CodeDependency.external_package.ilike(f"%{kw}%"))

        if dep_conditions:
            dep_stmt = (
                select(CodeDependency, RepositoryFile)
                .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
                .where(
                    RepositoryFile.snapshot_id == snapshot_id,
                    or_(*dep_conditions),
                )
                .limit(limit_per_signal)
            )
            dep_res = await session.execute(dep_stmt)
            for dep, f in dep_res.all():
                cid = f"dep:{dep.id}"
                candidates[cid] = RetrievedCandidate(
                    candidate_id=cid,
                    entity_type="DEPENDENCY",
                    name=dep.external_package or "dependency",
                    path=f.path,
                    start_line=dep.line_number,
                    end_line=dep.line_number,
                    content=f"Import {dep.external_package} at line {dep.line_number} in {f.path}",
                    file_id=f.id,
                    signals={"dependency_match": 0.75},
                )

        # 5. VECTOR SEARCH: Match chunks with precomputed embeddings using vector similarity
        effective_query_embedding = query_embedding
        if effective_query_embedding is None:
            query_text = (
                analyzed_query.raw_query.strip()
                if analyzed_query.raw_query and analyzed_query.raw_query.strip()
                else ""
            )
            if not query_text:
                query_parts = []
                if analyzed_query.keywords:
                    query_parts.extend(analyzed_query.keywords)
                if analyzed_query.symbol_candidates:
                    query_parts.extend(analyzed_query.symbol_candidates)
                if analyzed_query.concept_keywords:
                    query_parts.extend(analyzed_query.concept_keywords)
                query_text = " ".join(query_parts)

            if query_text:
                try:
                    from apps.api.src.services.code_atom.embedding import generate_code_embedding

                    effective_query_embedding = generate_code_embedding(
                        query_text, input_type="query"
                    )
                except Exception:
                    effective_query_embedding = None

                if effective_query_embedding is None:
                    effective_query_embedding = generate_text_embedding(query_text)

        if effective_query_embedding is not None:
            vec_stmt = (
                select(CodeChunk)
                .where(
                    CodeChunk.snapshot_id == snapshot_id,
                    CodeChunk.embedding.isnot(None),
                )
                .limit(limit_per_signal * 3)
            )
            vec_res = await session.execute(vec_stmt)
            vector_chunks = vec_res.scalars().all()
            scored_vector_chunks = []
            for chunk in vector_chunks:
                if chunk.embedding:
                    sim = compute_cosine_similarity(effective_query_embedding, chunk.embedding)
                    if sim > 0.2:
                        scored_vector_chunks.append((sim, chunk))
            scored_vector_chunks.sort(key=lambda x: x[0], reverse=True)
            for sim, chunk in scored_vector_chunks[:limit_per_signal]:
                cid = f"chunk:{chunk.id}"
                chunk_meta = _extract_chunk_metadata(chunk)
                if cid in candidates:
                    candidates[cid].signals["vector_similarity"] = sim
                    candidates[cid].signals["semantic_match"] = max(
                        candidates[cid].signals.get("semantic_match", 0.0), sim
                    )
                    if chunk_meta:
                        candidates[cid].metadata.update(chunk_meta)
                else:
                    candidates[cid] = RetrievedCandidate(
                        candidate_id=cid,
                        entity_type="CHUNK",
                        name=chunk.name,
                        path=chunk.path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        file_id=chunk.file_id,
                        symbol_id=chunk.symbol_id,
                        signals={"vector_similarity": sim, "semantic_match": sim},
                        metadata=chunk_meta,
                    )

        # 6. SEMANTIC / CONCEPT SEARCH: Match domain concept synonyms across chunks and symbols
        if analyzed_query.concept_keywords:
            concept_chunk_conditions = []
            for concept in analyzed_query.concept_keywords:
                if len(concept) >= 3:
                    concept_chunk_conditions.append(CodeChunk.name.ilike(f"%{concept}%"))
                    concept_chunk_conditions.append(CodeChunk.content.ilike(f"%{concept}%"))
                    concept_chunk_conditions.append(CodeChunk.commit_message.ilike(f"%{concept}%"))

            if concept_chunk_conditions:
                concept_chunk_stmt = (
                    select(CodeChunk)
                    .where(
                        CodeChunk.snapshot_id == snapshot_id,
                        or_(*concept_chunk_conditions),
                    )
                    .limit(limit_per_signal)
                )
                concept_chunk_res = await session.execute(concept_chunk_stmt)
                for chunk in concept_chunk_res.scalars().all():
                    cid = f"chunk:{chunk.id}"
                    chunk_meta = _extract_chunk_metadata(chunk)
                    if cid in candidates:
                        candidates[cid].signals["semantic_match"] = max(
                            candidates[cid].signals.get("semantic_match", 0.0), 0.85
                        )
                        if chunk_meta:
                            candidates[cid].metadata.update(chunk_meta)
                    else:
                        candidates[cid] = RetrievedCandidate(
                            candidate_id=cid,
                            entity_type="CHUNK",
                            name=chunk.name,
                            path=chunk.path,
                            start_line=chunk.start_line,
                            end_line=chunk.end_line,
                            content=chunk.content,
                            file_id=chunk.file_id,
                            symbol_id=chunk.symbol_id,
                            signals={"semantic_match": 0.85},
                            metadata=chunk_meta,
                        )

            # Match concept keywords in symbols
            concept_sym_conditions = []
            for concept in analyzed_query.concept_keywords:
                if len(concept) >= 3:
                    concept_sym_conditions.append(CodeSymbol.name.ilike(f"%{concept}%"))
                    concept_sym_conditions.append(CodeSymbol.qualified_name.ilike(f"%{concept}%"))

            if concept_sym_conditions:
                concept_sym_stmt = (
                    select(CodeSymbol, RepositoryFile)
                    .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                    .where(
                        RepositoryFile.snapshot_id == snapshot_id,
                        or_(*concept_sym_conditions),
                    )
                    .limit(limit_per_signal)
                )
                concept_sym_res = await session.execute(concept_sym_stmt)
                for sym, f in concept_sym_res.all():
                    cid = f"sym:{sym.id}"
                    if cid in candidates:
                        candidates[cid].signals["semantic_match"] = max(
                            candidates[cid].signals.get("semantic_match", 0.0), 0.85
                        )
                    else:
                        candidates[cid] = RetrievedCandidate(
                            candidate_id=cid,
                            entity_type="SYMBOL",
                            name=sym.name,
                            path=f.path,
                            start_line=sym.start_line,
                            end_line=sym.end_line,
                            content=f"{sym.symbol_type.value} {sym.qualified_name} (lines {sym.start_line}-{sym.end_line} in {f.path})",
                            file_id=f.id,
                            symbol_id=sym.id,
                            signals={"semantic_match": 0.85},
                        )

        # 7. ORDER CANDIDATES BY QUERY RELEVANCE
        weights = {
            "symbol_match": 1.5,
            "file_match": 1.3,
            "vector_similarity": 1.4,
            "semantic_match": 1.2,
            "content_match": 1.1,
            "dependency_match": 0.9,
        }

        def initial_score(c: RetrievedCandidate) -> float:
            return sum(c.signals.get(k, 0.0) * w for k, w in weights.items())

        ordered_candidates = sorted(candidates.values(), key=initial_score, reverse=True)
        return ordered_candidates
