import json
import uuid
from datetime import UTC, datetime

from apps.api.src.schemas.code_atom import (
    FactConfidence,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom import (
    CodeEntityResolver,
    TemporalRelationResolver,
    reconcile_code_relationships,
)
from apps.api.src.services.code_atom.relation_resolver import (
    canonicalize_file_path,
    generate_reconciled_fingerprint,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


def test_same_qualified_symbol_recognized_consistently():
    """1. Same qualified symbol across commits is recognized consistently."""
    resolver = CodeEntityResolver()

    # Identical qualified symbols
    id1 = resolver.build_qualified_identifier("authenticate_token", "apps/api/src/auth.py")
    id2 = resolver.build_qualified_identifier("authenticate_token", "apps/api/src/auth.py")
    assert id1 == id2 == "apps/api/src/auth.py::authenticate_token"

    # With backslashes vs forward slashes
    id3 = resolver.build_qualified_identifier("authenticate_token", "apps\\api\\src\\auth.py")
    assert id1 == id3

    # Path canonicalization
    assert canonicalize_file_path("apps\\api\\src\\auth.py") == "apps/api/src/auth.py"

    # Equivalence check
    assert resolver.are_entities_equivalent(id1, id3) is True
    assert resolver.are_entities_equivalent("apps/api/src/auth.py::authenticate_token", "apps/api/src/auth.py::authenticate_token") is True


def test_verified_renames_preserve_identity_and_provenance():
    """2. Verified renames preserve identity and historical provenance."""
    rename_history = {
        "apps/api/src/auth_old.py": "apps/api/src/auth.py",
        "apps/api/src/legacy/utils.py": "apps/api/src/common/utils.py",
    }
    resolver = CodeEntityResolver()

    # Old path vs new path under rename history
    canon_id, aliases = resolver.resolve_entity(
        name="verify_credentials",
        file_path="apps/api/src/auth_old.py",
        rename_history=rename_history,
    )
    assert canon_id == "apps/api/src/auth.py::verify_credentials"
    assert "verify_credentials" in aliases
    assert "apps/api/src/auth_old.py::verify_credentials" in aliases

    # Cross-equivalence under rename
    assert resolver.are_entities_equivalent(
        "apps/api/src/auth_old.py::verify_credentials",
        "apps/api/src/auth.py::verify_credentials",
        rename_history=rename_history,
    ) is True


def test_distinct_symbols_with_similar_names_remain_distinct():
    """3. Distinct symbols with similar names remain strictly distinct."""
    resolver = CodeEntityResolver()

    # Similar but distinct names in same file
    assert resolver.are_entities_equivalent(
        "apps/api/src/auth.py::authenticate_user",
        "apps/api/src/auth.py::authenticate_token",
    ) is False

    # Similar names in different files
    assert resolver.are_entities_equivalent(
        "apps/api/src/user.py::validate",
        "apps/api/src/session.py::validate",
    ) is False

    # When reconciling relations, distinct symbols must never be merged
    r1 = TemporalCodeRelation(
        id="rel-1",
        subject="apps/api/src/auth.py::authenticate_user",
        relation=RelationType.CALLS,
        object="db.py::get_user",
        fingerprint="fp1",
    )
    r2 = TemporalCodeRelation(
        id="rel-2",
        subject="apps/api/src/auth.py::authenticate_token",
        relation=RelationType.CALLS,
        object="db.py::get_user",
        fingerprint="fp2",
    )
    reconciled = reconcile_code_relationships([r1, r2])
    assert len(reconciled) == 2
    subjects = {r.canonical_subject for r in reconciled}
    assert "apps/api/src/auth.py::authenticate_user" in subjects
    assert "apps/api/src/auth.py::authenticate_token" in subjects


def test_equivalent_relationships_deduplicated_deterministically():
    """4. Equivalent relationship labels normalized and deduplicated deterministically."""
    t1 = datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC)
    r1 = TemporalCodeRelation(
        id="rel-a",
        subject="OrderProcessor",
        relation=RelationType.CALLS,
        object="PaymentGateway.charge",
        t_start=t1,
        commit_sha="commit-111",
        source_fact_id="fact-1",
        fingerprint="fp-a",
    )
    # Same relationship expressed with string or equivalent relation
    r2 = TemporalCodeRelation(
        id="rel-b",
        subject="OrderProcessor",
        relation="invokes",  # Will normalize to CALLS
        object="PaymentGateway.charge",
        t_start=t1,
        commit_sha="commit-222",
        source_fact_id="fact-2",
        fingerprint="fp-b",
    )

    reconciled = reconcile_code_relationships([r1, r2])
    assert len(reconciled) == 1
    rec = reconciled[0]
    assert rec.relation == RelationType.CALLS
    assert rec.canonical_subject == "OrderProcessor"
    assert rec.canonical_object == "PaymentGateway.charge"
    assert "commit-111" in rec.history_commit_shas
    assert "commit-222" in rec.history_commit_shas
    assert "fact-1" in rec.history_fact_ids
    assert "fact-2" in rec.history_fact_ids
    assert rec.provenance["resolved_sources_count"] == 2


def test_reprocessing_is_idempotent():
    """5. Reprocessing reconciled relations is completely idempotent."""
    t_start = datetime(2026, 1, 1, tzinfo=UTC)
    t_end = datetime(2026, 4, 1, tzinfo=UTC)
    r1 = TemporalCodeRelation(
        id="rel-1",
        subject="Service::handler",
        relation=RelationType.CALLS,
        object="DB::query",
        t_start=t_start,
        t_end=t_end,
        commit_sha="c1",
        fingerprint="fp1",
    )
    resolver_inst = TemporalRelationResolver()
    pass1 = resolver_inst.reconcile_relations([r1])
    pass2 = reconcile_code_relationships(pass1)
    pass3 = reconcile_code_relationships(pass2)

    assert len(pass1) == 1
    assert len(pass2) == 1
    assert len(pass3) == 1
    assert pass1[0].fingerprint == pass2[0].fingerprint == pass3[0].fingerprint
    assert pass1[0].canonical_subject == pass2[0].canonical_subject
    assert pass1[0].canonical_object == pass2[0].canonical_object
    assert pass1[0].t_start == pass2[0].t_start
    assert pass1[0].t_end == pass2[0].t_end

    fp = generate_reconciled_fingerprint(
        canonical_subject="Service::handler",
        relation=RelationType.CALLS,
        canonical_object="DB::query",
        t_start=t_start,
        t_end=t_end,
    )
    assert len(fp) == 64


def test_verified_timestamps_retained_during_reconciliation():
    """6. Verified start and end timestamps retained during reconciliation."""
    t_intro = datetime(2026, 1, 15, tzinfo=UTC)
    t_removal = datetime(2026, 5, 20, tzinfo=UTC)
    t_obs1 = datetime(2026, 2, 1, tzinfo=UTC)
    t_obs2 = datetime(2026, 5, 20, tzinfo=UTC)

    # Event 1: Introduction of dependency
    r_intro = TemporalCodeRelation(
        id="rel-intro",
        subject="app.py::main",
        relation=RelationType.REFERENCES,
        object="lib.py::helper",
        t_start=t_intro,
        t_end=None,
        t_obs=t_obs1,
        commit_sha="sha-intro",
        fingerprint="fp-intro",
    )

    # Event 2: Removal of dependency
    r_removal = TemporalCodeRelation(
        id="rel-rem",
        subject="app.py::main",
        relation=RelationType.REFERENCES,
        object="lib.py::helper",
        t_start=None,
        t_end=t_removal,
        t_obs=t_obs2,
        commit_sha="sha-rem",
        fingerprint="fp-rem",
    )

    reconciled = reconcile_code_relationships([r_intro, r_removal])
    assert len(reconciled) == 1
    res = reconciled[0]
    assert res.t_start == t_intro
    assert res.t_end == t_removal
    assert res.t_obs == t_obs2
    assert res.has_temporal_conflict is False


def test_missing_timestamps_do_not_erase_verified_or_fabricate():
    """7. Missing timestamps never erase verified timestamps or fabricate dates."""
    t_verified = datetime(2026, 3, 10, tzinfo=UTC)

    r_with_time = TemporalCodeRelation(
        id="rel-time",
        subject="service.py::run",
        relation=RelationType.CALLS,
        object="worker.py::enqueue",
        t_start=t_verified,
        fingerprint="fp-time",
    )
    r_without_time = TemporalCodeRelation(
        id="rel-notime",
        subject="service.py::run",
        relation=RelationType.CALLS,
        object="worker.py::enqueue",
        t_start=None,
        t_end=None,
        t_obs=None,
        fingerprint="fp-notime",
    )

    # Reconciling keeps verified t_start and leaves t_end as None
    reconciled = reconcile_code_relationships([r_with_time, r_without_time])
    assert len(reconciled) == 1
    assert reconciled[0].t_start == t_verified
    assert reconciled[0].t_end is None

    # Two relations with None timestamps remain None (no fabricated dates)
    r_none1 = TemporalCodeRelation(
        id="rel-none1",
        subject="A",
        relation=RelationType.IMPORTS,
        object="B",
        fingerprint="fp-none1",
    )
    r_none2 = TemporalCodeRelation(
        id="rel-none2",
        subject="A",
        relation=RelationType.IMPORTS,
        object="B",
        fingerprint="fp-none2",
    )
    rec_nones = reconcile_code_relationships([r_none1, r_none2])
    assert len(rec_nones) == 1
    assert rec_nones[0].t_start is None
    assert rec_nones[0].t_end is None


def test_removal_events_correctly_end_relationships():
    """8. Removal events correctly record validity end without guessing start."""
    t_end = datetime(2026, 6, 1, tzinfo=UTC)
    r_del = TemporalCodeRelation(
        id="rel-del",
        subject="BillingService",
        relation=RelationType.CALLS,
        object="LegacyStripeClient",
        t_start=None,
        t_end=t_end,
        commit_sha="sha-del",
        fingerprint="fp-del",
    )
    reconciled = reconcile_code_relationships([r_del])
    assert len(reconciled) == 1
    assert reconciled[0].t_start is None
    assert reconciled[0].t_end == t_end
    assert reconciled[0].has_temporal_conflict is False


def test_conflicting_temporal_evidence_preserved_and_flagged():
    """9. Conflicting temporal evidence is preserved and flagged safely."""
    # Conflict: validity end is strictly earlier than start
    t_start = datetime(2026, 8, 1, tzinfo=UTC)
    t_end = datetime(2026, 2, 1, tzinfo=UTC)

    r_start = TemporalCodeRelation(
        id="r-start",
        subject="Pipeline",
        relation=RelationType.CALLS,
        object="Stage1",
        t_start=t_start,
        fingerprint="fp-s",
    )
    r_end = TemporalCodeRelation(
        id="r-end",
        subject="Pipeline",
        relation=RelationType.CALLS,
        object="Stage1",
        t_end=t_end,
        fingerprint="fp-e",
    )

    reconciled = reconcile_code_relationships([r_start, r_end])
    assert len(reconciled) == 1
    rec = reconciled[0]
    assert rec.has_temporal_conflict is True
    assert rec.conflict_detail is not None
    assert "validity end" in rec.conflict_detail
    assert rec.is_uncertain is True
    assert rec.confidence == FactConfidence.UNCERTAIN
    # Timestamps are strictly preserved, not discarded or overwritten with guesses
    assert rec.t_start == t_start
    assert rec.t_end == t_end


def test_relationship_provenance_json_serializable():
    """10. Relationship provenance remains JSON-serializable."""
    t1 = datetime(2026, 3, 1, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, tzinfo=UTC)
    r_conflict = TemporalCodeRelation(
        id="rc",
        subject="Core::app",
        relation=RelationType.REFERENCES,
        object="Lib::sub",
        t_start=t1,
        t_end=t2,
        commit_sha="c123",
        source_fact_id="fact-xyz",
        provenance={"sample_key": "sample_val"},
        fingerprint="fp-c",
    )
    reconciled = reconcile_code_relationships([r_conflict])
    rec = reconciled[0]

    dumped = rec.model_dump(mode="json")
    serialized = json.dumps(dumped)
    deserialized = json.loads(serialized)

    assert deserialized["has_temporal_conflict"] is True
    assert "validity end" in deserialized["conflict_detail"]
    assert "c123" in deserialized["history_commit_shas"]
    assert "fact-xyz" in deserialized["history_fact_ids"]
    assert deserialized["provenance"]["temporal_conflict"] is not None


def test_context_assembler_formats_canonical_and_conflict_relations():
    """11. ContextAssembler formats canonical entities and temporal conflict tags correctly."""
    assembler = ContextAssembler()
    cand = RankedCandidate(
        candidate=RetrievedCandidate(
            candidate_id=str(uuid.uuid4()),
            entity_type="CHUNK",
            name="process_request",
            path="apps/api/src/service.py",
            start_line=10,
            end_line=30,
            content="def process_request(): pass",
            file_id=uuid.uuid4(),
            metadata={
                "temporal_relations": [
                    {
                        "subject": "service.py::process_request",
                        "canonical_subject": "apps/api/src/service.py::process_request",
                        "relation": "CALLS",
                        "object": "auth.py::verify",
                        "canonical_object": "apps/api/src/auth.py::verify",
                        "t_start": "2026-01-01T00:00:00Z",
                        "t_end": None,
                        "has_temporal_conflict": False,
                    },
                    {
                        "subject": "service.py::process_request",
                        "canonical_subject": "apps/api/src/service.py::process_request",
                        "relation": "CALLS",
                        "object": "legacy.py::old_check",
                        "canonical_object": "apps/api/src/legacy.py::old_check",
                        "t_start": "2026-05-01T00:00:00Z",
                        "t_end": "2026-02-01T00:00:00Z",
                        "has_temporal_conflict": True,
                    },
                ]
            },
        ),
        score=0.95,
        matched_reasons=["semantic_match"],
    )

    assembled = assembler.assemble_context([cand])
    assert "apps/api/src/service.py::process_request" in assembled.prompt_context
    assert "apps/api/src/auth.py::verify" in assembled.prompt_context
    assert "(conflict)" in assembled.prompt_context
