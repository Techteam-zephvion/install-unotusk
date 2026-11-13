import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.schemas.code_atom import (
    FactConfidence,
    PropertyExclusivity,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom.relation_resolver import CodeEntityResolver
from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy
from apps.api.src.services.evokg.contradiction import (
    ContradictionResolutionResult,
    EvoKGContradictionEngine,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvoKGPersistenceService:
    """
    Persistence Adapter connecting EvoKG Contradiction Engine (T2.2) to PostgreSQL (T2.3).

    Responsibilities:
    1. Canonicalizes incoming code relation entities and scope keys.
    2. Loads existing active assertions for the target repository & branch under row-level locking.
    3. Invokes EvoKGContradictionEngine deterministically to resolve supersessions and conflicts.
    4. Persists new triplets, updates superseded intervals, and retains uncertain evidence safely.
    5. Enforces fingerprint-based idempotency and branch isolation.
    6. Provides optimized indexed queries for active and historical graph traversal.
    """

    def __init__(
        self,
        contradiction_engine: EvoKGContradictionEngine | None = None,
        entity_resolver: CodeEntityResolver | None = None,
    ):
        self.contradiction_engine = contradiction_engine or EvoKGContradictionEngine()
        self.entity_resolver = entity_resolver or CodeEntityResolver()

    # -------------------------------------------------------------------------
    # Core Ingestion & Persistence
    # -------------------------------------------------------------------------

    async def persist_relations(
        self,
        session: AsyncSession,
        repository_id: uuid.UUID,
        relations: list[TemporalCodeRelation],
        branch: str = "main",
        snapshot_id: uuid.UUID | None = None,
        commit_sha: str | None = None,
        commit_parents: dict[str, list[str]] | None = None,
        files_map: dict[str, uuid.UUID] | None = None,
        symbols_map: dict[str, uuid.UUID] | None = None,
        rename_history: dict[str, str] | None = None,
    ) -> ContradictionResolutionResult:
        """
        Incrementally processes and persists a batch of TemporalCodeRelations into evokg_triplets.

        Guarantees:
        - Atomic and transactional within the provided session.
        - Idempotent: repeated ingestion of identical fingerprints produces no duplicates.
        - Branch-isolated: does not cross branch boundaries unless verified merge ancestry exists.
        - Deterministic: contradiction resolution order is independent of caller input order.
        - Open-world safe: does not terminate assertions absent from partial batches.
        """
        if not relations:
            return ContradictionResolutionResult()

        files_map = files_map or {}
        symbols_map = symbols_map or {}
        rename_history = rename_history or {}

        # Configure contradiction engine with commit DAG and rename history
        engine = EvoKGContradictionEngine(
            commit_parents=commit_parents,
            rename_history=rename_history,
            default_branch=branch,
        )

        # 1. Normalize and canonicalize incoming relations
        prepared_relations: list[TemporalCodeRelation] = []
        relevant_subjects: set[str] = set()

        for rel in relations:
            prep = self._normalize_relation(rel, branch=branch, default_commit=commit_sha)
            prepared_relations.append(prep)
            if prep.canonical_subject:
                relevant_subjects.add(prep.canonical_subject)
            if prep.subject:
                relevant_subjects.add(prep.subject)

        if not relevant_subjects:
            return ContradictionResolutionResult()

        # 2. Query existing active assertions for the affected subjects under row-level lock
        query = (
            select(EvoKGTriplet)
            .where(
                EvoKGTriplet.repository_id == repository_id,
                EvoKGTriplet.branch == branch,
                EvoKGTriplet.valid_to.is_(None),  # Active assertions only
                EvoKGTriplet.subject_id.in_(list(relevant_subjects)),
            )
        )

        # Apply FOR UPDATE concurrency lock when running on PostgreSQL
        if session.bind and session.bind.dialect.name == "postgresql":
            query = query.with_for_update()

        existing_res = await session.execute(query)
        existing_triplets = list(existing_res.scalars().all())

        # Map active DB triplets to TemporalCodeRelation for the pure contradiction engine
        existing_relations: list[TemporalCodeRelation] = []
        triplet_by_id: dict[str, EvoKGTriplet] = {}

        for t in existing_triplets:
            rel_id = str(t.id)
            t_rel = self._triplet_to_relation(t)
            existing_relations.append(t_rel)
            triplet_by_id[rel_id] = t

        # 3. Execute pure in-memory contradiction resolution
        resolution_result = engine.resolve_contradictions(
            relations=prepared_relations,
            existing_relations=existing_relations,
        )

        # 4. Check existing fingerprints in DB to guarantee idempotency
        all_incoming_candidates = (
            resolution_result.active_relations
            + resolution_result.superseded_relations
            + resolution_result.conflicting_relations
            + resolution_result.historical_relations
        )
        fps = [r.fingerprint for r in all_incoming_candidates if r.fingerprint]
        existing_fps: set[str] = set()
        if fps:
            fp_query = select(EvoKGTriplet.fingerprint).where(
                EvoKGTriplet.repository_id == repository_id,
                EvoKGTriplet.fingerprint.in_(fps),
            )
            fp_res = await session.execute(fp_query)
            existing_fps = set(fp_res.scalars().all())

        # 5. Terminate validity intervals on superseded existing DB records
        closed_candidates = (
            resolution_result.superseded_relations + resolution_result.historical_relations
        )
        for sup_rel in closed_candidates:
            if sup_rel.id in triplet_by_id:
                existing_t = triplet_by_id[sup_rel.id]
                existing_t.valid_to = sup_rel.t_end or utc_now()

        # 6. Persist newly introduced triplets
        new_triplets_created: dict[str, EvoKGTriplet] = {}
        for cand_rel in all_incoming_candidates:
            # Skip if already exists in DB (either existing active row or matching fingerprint)
            if cand_rel.id in triplet_by_id:
                continue
            if cand_rel.fingerprint in existing_fps:
                continue

            # Resolve foreign key pointers
            file_id = files_map.get(cand_rel.file_path) if cand_rel.file_path else None
            symbol_id = None
            if cand_rel.symbol_name:
                symbol_id = symbols_map.get(cand_rel.symbol_name)
                if not symbol_id and file_id:
                    symbol_id = symbols_map.get(f"{file_id}:{cand_rel.symbol_name}")

            # Assign deterministic or new UUID
            try:
                triplet_uuid = uuid.UUID(cand_rel.id)
            except (ValueError, TypeError):
                triplet_uuid = uuid.uuid4()

            conf_str = (
                cand_rel.confidence.value
                if hasattr(cand_rel.confidence, "value")
                else str(cand_rel.confidence)
            )

            new_t = EvoKGTriplet(
                id=triplet_uuid,
                repository_id=repository_id,
                snapshot_id=snapshot_id,
                branch=branch,
                subject_id=cand_rel.canonical_subject or cand_rel.subject,
                relation=(
                    cand_rel.relation.value
                    if hasattr(cand_rel.relation, "value")
                    else str(cand_rel.relation)
                ),
                object_id=cand_rel.canonical_object or cand_rel.object,
                file_id=file_id,
                symbol_id=symbol_id,
                is_exclusive=cand_rel.is_exclusive,
                scope_key=cand_rel.scope_key,
                valid_from=cand_rel.t_start,
                valid_to=cand_rel.t_end,
                observation_time=cand_rel.t_obs or utc_now(),
                commit_sha=cand_rel.commit_sha or commit_sha,
                confidence_score=cand_rel.confidence_score,
                confidence_level=conf_str,
                is_uncertain=cand_rel.is_uncertain,
                has_temporal_conflict=cand_rel.has_temporal_conflict,
                conflict_detail=cand_rel.conflict_detail,
                file_path=cand_rel.file_path,
                symbol_name=cand_rel.symbol_name,
                line_start=cand_rel.provenance.get("line_start"),
                line_end=cand_rel.provenance.get("line_end"),
                fingerprint=cand_rel.fingerprint,
                provenance=dict(cand_rel.provenance) if cand_rel.provenance else {},
            )

            session.add(new_t)
            new_triplets_created[cand_rel.id] = new_t
            existing_fps.add(cand_rel.fingerprint)

        # Flush new triplets so foreign keys exist in PostgreSQL before updating supersession pointers
        await session.flush()

        # 7. Reconcile forward and backward supersession references
        for sup_rel in closed_candidates:
            if sup_rel.id in triplet_by_id and sup_rel.superseded_by_id:
                try:
                    triplet_by_id[sup_rel.id].superseded_by_id = uuid.UUID(sup_rel.superseded_by_id)
                except (ValueError, TypeError):
                    pass

        for cand_rel in all_incoming_candidates:
            if cand_rel.id in new_triplets_created:
                current_t = new_triplets_created[cand_rel.id]
                if cand_rel.supersedes_id and not current_t.supersedes_id:
                    try:
                        current_t.supersedes_id = uuid.UUID(cand_rel.supersedes_id)
                    except (ValueError, TypeError):
                        pass

                if cand_rel.superseded_by_id and not current_t.superseded_by_id:
                    if cand_rel.superseded_by_id in new_triplets_created:
                        current_t.superseded_by_id = new_triplets_created[cand_rel.superseded_by_id].id
                    elif cand_rel.superseded_by_id in triplet_by_id:
                        current_t.superseded_by_id = triplet_by_id[cand_rel.superseded_by_id].id

        await session.flush()
        return resolution_result

    # -------------------------------------------------------------------------
    # Indexed Query APIs for Active and Temporal Traversal
    # -------------------------------------------------------------------------

    async def get_active_outgoing(
        self,
        session: AsyncSession,
        repository_id: uuid.UUID,
        subject_id: str,
        branch: str = "main",
        relation: str | None = None,
        include_conflicts: bool = False,
    ) -> list[EvoKGTriplet]:
        """Queries active (valid_to IS NULL) outgoing relationships for an entity."""
        filters = [
            EvoKGTriplet.repository_id == repository_id,
            EvoKGTriplet.branch == branch,
            EvoKGTriplet.subject_id == subject_id,
            EvoKGTriplet.valid_to.is_(None),
        ]
        if not include_conflicts:
            filters.append(EvoKGTriplet.is_uncertain.is_(False))
            filters.append(EvoKGTriplet.has_temporal_conflict.is_(False))
        if relation:
            filters.append(EvoKGTriplet.relation == relation)

        stmt = select(EvoKGTriplet).where(and_(*filters)).order_by(EvoKGTriplet.valid_from.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def get_active_incoming(
        self,
        session: AsyncSession,
        repository_id: uuid.UUID,
        object_id: str,
        branch: str = "main",
        relation: str | None = None,
        include_conflicts: bool = False,
    ) -> list[EvoKGTriplet]:
        """Queries active (valid_to IS NULL) incoming relationships pointing to an entity."""
        filters = [
            EvoKGTriplet.repository_id == repository_id,
            EvoKGTriplet.branch == branch,
            EvoKGTriplet.object_id == object_id,
            EvoKGTriplet.valid_to.is_(None),
        ]
        if not include_conflicts:
            filters.append(EvoKGTriplet.is_uncertain.is_(False))
            filters.append(EvoKGTriplet.has_temporal_conflict.is_(False))
        if relation:
            filters.append(EvoKGTriplet.relation == relation)

        stmt = select(EvoKGTriplet).where(and_(*filters)).order_by(EvoKGTriplet.valid_from.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def get_temporal_history(
        self,
        session: AsyncSession,
        repository_id: uuid.UUID,
        subject_id: str,
        branch: str = "main",
        as_of: datetime | None = None,
        relation: str | None = None,
    ) -> list[EvoKGTriplet]:
        """
        Queries point-in-time or full historical evolution of relationships for an entity.
        If as_of is provided, returns triplets valid at that timestamp:
        valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of).
        """
        filters = [
            EvoKGTriplet.repository_id == repository_id,
            EvoKGTriplet.branch == branch,
            EvoKGTriplet.subject_id == subject_id,
        ]
        if relation:
            filters.append(EvoKGTriplet.relation == relation)

        if as_of:
            as_of_tz = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)
            filters.append(
                and_(
                    or_(EvoKGTriplet.valid_from.is_(None), EvoKGTriplet.valid_from <= as_of_tz),
                    or_(EvoKGTriplet.valid_to.is_(None), EvoKGTriplet.valid_to > as_of_tz),
                )
            )

        stmt = select(EvoKGTriplet).where(and_(*filters)).order_by(EvoKGTriplet.valid_from.asc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def get_conflicts(
        self,
        session: AsyncSession,
        repository_id: uuid.UUID,
        branch: str = "main",
        subject_id: str | None = None,
    ) -> list[EvoKGTriplet]:
        """Queries triplets flagged with temporal conflicts or uncertainty."""
        filters = [
            EvoKGTriplet.repository_id == repository_id,
            EvoKGTriplet.branch == branch,
            or_(
                EvoKGTriplet.has_temporal_conflict.is_(True),
                EvoKGTriplet.is_uncertain.is_(True),
            ),
        ]
        if subject_id:
            filters.append(EvoKGTriplet.subject_id == subject_id)

        stmt = select(EvoKGTriplet).where(and_(*filters)).order_by(EvoKGTriplet.observation_time.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _normalize_relation(
        self,
        rel: TemporalCodeRelation,
        branch: str,
        default_commit: str | None = None,
    ) -> TemporalCodeRelation:
        """Normalizes and canonicalizes relation metadata."""
        copy_rel = rel.model_copy()

        # 1. Canonicalize subject and object
        raw_subj = copy_rel.canonical_subject or copy_rel.subject
        canon_sub, _ = self.entity_resolver.resolve_entity(
            name=raw_subj,
            file_path=copy_rel.file_path,
        )
        copy_rel.canonical_subject = canon_sub

        raw_obj = copy_rel.canonical_object or copy_rel.object
        canon_obj, _ = self.entity_resolver.resolve_entity(
            name=raw_obj,
            file_path=copy_rel.file_path,
        )
        copy_rel.canonical_object = canon_obj

        # 2. Exclusivity & Scope Key classification via T2.1 taxonomy
        tax_entry = CodeRelationTaxonomy.classify(copy_rel.relation)
        copy_rel.is_exclusive = tax_entry.exclusivity == PropertyExclusivity.EXCLUSIVE

        if not copy_rel.scope_key or copy_rel.scope_key == "default":
            key, uncertain = CodeRelationTaxonomy.generate_scope_key(
                copy_rel.relation,
                symbol_name=copy_rel.symbol_name,
            )
            copy_rel.scope_key = key
            if uncertain:
                copy_rel.is_uncertain = True

        # 3. Provenance and commit SHA
        prov = dict(copy_rel.provenance or {})
        if "branch" not in prov:
            prov["branch"] = branch
        if not copy_rel.commit_sha and default_commit:
            copy_rel.commit_sha = default_commit
            prov["commit_sha"] = default_commit
        copy_rel.provenance = prov

        return copy_rel

    @staticmethod
    def _triplet_to_relation(t: EvoKGTriplet) -> TemporalCodeRelation:
        """Converts an EvoKGTriplet model instance into a TemporalCodeRelation schema."""
        conf_enum = (
            FactConfidence(t.confidence_level)
            if t.confidence_level in FactConfidence._value2member_map_
            else FactConfidence.UNCERTAIN
        )
        t_start = t.valid_from
        if t_start is not None and t_start.tzinfo is None:
            t_start = t_start.replace(tzinfo=UTC)

        t_end = t.valid_to
        if t_end is not None and t_end.tzinfo is None:
            t_end = t_end.replace(tzinfo=UTC)

        t_obs = t.observation_time
        if t_obs is not None and t_obs.tzinfo is None:
            t_obs = t_obs.replace(tzinfo=UTC)

        return TemporalCodeRelation(
            id=str(t.id),
            subject=t.subject_id,
            canonical_subject=t.subject_id,
            relation=t.relation,
            object=t.object_id,
            canonical_object=t.object_id,
            t_start=t_start,
            t_end=t_end,
            t_obs=t_obs,
            confidence=conf_enum,
            confidence_score=t.confidence_score,
            is_uncertain=t.is_uncertain,
            has_temporal_conflict=t.has_temporal_conflict,
            conflict_detail=t.conflict_detail,
            is_exclusive=t.is_exclusive,
            scope_key=t.scope_key,
            commit_sha=t.commit_sha,
            file_path=t.file_path,
            symbol_name=t.symbol_name,
            fingerprint=t.fingerprint,
            superseded_by_id=str(t.superseded_by_id) if t.superseded_by_id else None,
            supersedes_id=str(t.supersedes_id) if t.supersedes_id else None,
            provenance=dict(t.provenance) if t.provenance else {},
        )
