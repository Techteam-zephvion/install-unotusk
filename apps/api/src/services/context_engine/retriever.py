import uuid
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery


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


class MultiSignalRetriever:
    @staticmethod
    async def retrieve_candidates(
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        analyzed_query: AnalyzedQuery,
        limit_per_signal: int = 15,
    ) -> list[RetrievedCandidate]:
        candidates: dict[str, RetrievedCandidate] = {}

        # 1. FILE SEARCH: Match paths & filenames
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
                exact_path = any(p in f.path.lower() for p in analyzed_query.path_candidates)
                score = 1.0 if exact_path else 0.7
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

        # 2. SYMBOL SEARCH: Match symbol names (classes, functions, methods, types)
        symbol_conditions = []
        for sym in analyzed_query.symbol_candidates:
            symbol_conditions.append(CodeSymbol.name.ilike(sym))
            symbol_conditions.append(CodeSymbol.qualified_name.ilike(f"%{sym}%"))
        for kw in analyzed_query.keywords:
            if len(kw) >= 3:
                symbol_conditions.append(CodeSymbol.name.ilike(f"%{kw}%"))

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
                exact_sym = any(
                    s.lower() == sym.name.lower() for s in analyzed_query.symbol_candidates
                )
                score = 1.2 if exact_sym else 0.8
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

        # 3. CONTENT / CODE CHUNK SEARCH: Match code bodies and comments
        chunk_conditions = []
        for kw in analyzed_query.keywords:
            if len(kw) >= 3:
                chunk_conditions.append(CodeChunk.name.ilike(f"%{kw}%"))
                chunk_conditions.append(CodeChunk.content.ilike(f"%{kw}%"))
        for sym in analyzed_query.symbol_candidates:
            chunk_conditions.append(CodeChunk.content.ilike(f"%{sym}%"))

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
                if cid in candidates:
                    candidates[cid].signals["content_match"] = 0.8
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
                        signals={"content_match": 0.8},
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

        return list(candidates.values())
