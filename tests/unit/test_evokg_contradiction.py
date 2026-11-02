"""
Unit Tests for EvoKG Contradiction Engine and Temporal Lifecycle Resolver (T2.2 Milestone).
Reference: arXiv:2509.15464 (EvoReasoner / EvoKG §3.2).
"""

import random
from datetime import UTC, datetime, timedelta

from apps.api.src.schemas.code_atom import (
    FactConfidence,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.evokg.contradiction import (
    EvoKGContradictionEngine,
    ResolutionAction,
)


def _dt(hours_offset: int) -> datetime:
    """Helper creating UTC timestamps with fixed base."""
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    return base + timedelta(hours=hours_offset)


def test_1_exclusive_return_type_changes():
    """Verify that a high-confidence return type update supersedes the prior active assertion."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(2)

    rel_v1 = TemporalCodeRelation(
        id="rel-ret-1",
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="dict[str, Any]",
        t_start=t1,
        confidence=FactConfidence.HIGH,
        confidence_score=0.95,
        fingerprint="fp_ret_v1",
    )

    rel_v2 = TemporalCodeRelation(
        id="rel-ret-2",
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TokenPayloadDTO",
        t_start=t2,
        commit_sha="c222222",
        confidence=FactConfidence.HIGH,
        confidence_score=0.95,
        fingerprint="fp_ret_v2",
    )

    result = engine.resolve_contradictions(
        relations=[rel_v2],
        existing_relations=[rel_v1],
    )

    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-ret-2"
    assert result.active_relations[0].canonical_object == "TokenPayloadDTO"
    assert result.active_relations[0].t_end is None

    assert len(result.superseded_relations) == 1
    v1_superseded = result.superseded_relations[0]
    assert v1_superseded.id == "rel-ret-1"
    assert v1_superseded.t_end == t2
    assert v1_superseded.superseded_by_id == "rel-ret-2"
    assert v1_superseded.provenance.get("superseded_by_commit") == "c222222"

    diag = next(d for d in result.diagnostics if d.action == ResolutionAction.SUPERSEDED)
    assert diag.target_relation_id == "rel-ret-2"
    assert diag.superseded_relation_id == "rel-ret-1"


def test_2_signature_changes():
    """Verify that function parameter signature updates supersede prior signatures."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(3)

    sig_v1 = TemporalCodeRelation(
        id="rel-sig-1",
        subject="apps/api/src/order.py::create_order",
        relation=RelationType.HAS_SIGNATURE,
        object="(item_id: str, qty: int)",
        t_start=t1,
        confidence_score=0.95,
        fingerprint="fp_sig_v1",
    )

    sig_v2 = TemporalCodeRelation(
        id="rel-sig-2",
        subject="apps/api/src/order.py::create_order",
        relation=RelationType.HAS_SIGNATURE,
        object="(item_id: str, qty: int, user_id: str)",
        t_start=t2,
        confidence_score=0.95,
        fingerprint="fp_sig_v2",
    )

    result = engine.resolve_contradictions([sig_v2], existing_relations=[sig_v1])

    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-sig-2"
    assert len(result.superseded_relations) == 1
    assert result.superseded_relations[0].id == "rel-sig-1"
    assert result.superseded_relations[0].t_end == t2


def test_3_overload_slot_isolation():
    """Verify that updating overload slot 0 leaves overload slot 1 active and untouched."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(2)

    ov0_v1 = TemporalCodeRelation(
        id="rel-ov0-v1",
        subject="apps/api/src/math.py::calc",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="int",
        scope_key="overload:0",
        t_start=t1,
        confidence_score=0.95,
        fingerprint="fp_ov0_v1",
    )

    ov1_v1 = TemporalCodeRelation(
        id="rel-ov1-v1",
        subject="apps/api/src/math.py::calc",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="float",
        scope_key="overload:1",
        t_start=t1,
        confidence_score=0.95,
        fingerprint="fp_ov1_v1",
    )

    # Update overload:0 only
    ov0_v2 = TemporalCodeRelation(
        id="rel-ov0-v2",
        subject="apps/api/src/math.py::calc",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="Union[int, str]",
        scope_key="overload:0",
        t_start=t2,
        confidence_score=0.95,
        fingerprint="fp_ov0_v2",
    )

    result = engine.resolve_contradictions(
        relations=[ov0_v2],
        existing_relations=[ov0_v1, ov1_v1],
    )

    active_ids = {r.id for r in result.active_relations}
    assert "rel-ov0-v2" in active_ids
    assert "rel-ov1-v1" in active_ids  # overload:1 remains active!

    superseded_ids = {r.id for r in result.superseded_relations}
    assert "rel-ov0-v1" in superseded_ids
    assert "rel-ov1-v1" not in superseded_ids


def test_4_python_multiple_inheritance_slot_isolation():
    """Verify that Python multiple inheritance uses independent slots (base:0 vs base:1)."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(4)

    # Class Derived(BaseController, SessionMixin)
    base0_v1 = TemporalCodeRelation(
        id="rel-base0-v1",
        subject="apps/api/src/controller.py::AuthController",
        relation=RelationType.INHERITS,
        object="BaseController",
        scope_key="base:0",
        t_start=t1,
        confidence_score=0.95,
        fingerprint="fp_base0_v1",
    )

    base1_v1 = TemporalCodeRelation(
        id="rel-base1-v1",
        subject="apps/api/src/controller.py::AuthController",
        relation=RelationType.INHERITS,
        object="SessionMixin",
        scope_key="base:1",
        t_start=t1,
        confidence_score=0.95,
        fingerprint="fp_base1_v1",
    )

    # Replace SessionMixin with FastSessionMixin in base:1
    base1_v2 = TemporalCodeRelation(
        id="rel-base1-v2",
        subject="apps/api/src/controller.py::AuthController",
        relation=RelationType.INHERITS,
        object="FastSessionMixin",
        scope_key="base:1",
        t_start=t2,
        confidence_score=0.95,
        fingerprint="fp_base1_v2",
    )

    result = engine.resolve_contradictions(
        relations=[base1_v2],
        existing_relations=[base0_v1, base1_v1],
    )

    active_map = {r.scope_key: r for r in result.active_relations}
    assert active_map["base:0"].object == "BaseController"
    assert active_map["base:0"].t_end is None  # BaseController untouched!
    assert active_map["base:1"].object == "FastSessionMixin"

    assert len(result.superseded_relations) == 1
    assert result.superseded_relations[0].id == "rel-base1-v1"
    assert result.superseded_relations[0].superseded_by_id == "rel-base1-v2"


def test_5_non_exclusive_calls_concurrency():
    """Verify that non-exclusive relationships (CALLS) coexist concurrently without termination."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(2)

    call1 = TemporalCodeRelation(
        id="rel-call-1",
        subject="order_processor",
        relation=RelationType.CALLS,
        object="inventory_service.reserve",
        t_start=t1,
        fingerprint="fp_call_1",
    )

    call2 = TemporalCodeRelation(
        id="rel-call-2",
        subject="order_processor",
        relation=RelationType.CALLS,
        object="payment_gateway.charge",
        t_start=t2,
        fingerprint="fp_call_2",
    )

    result = engine.resolve_contradictions(
        relations=[call2],
        existing_relations=[call1],
    )

    assert len(result.active_relations) == 2
    assert len(result.superseded_relations) == 0
    assert len(result.conflicting_relations) == 0

    actions = [d.action for d in result.diagnostics]
    assert ResolutionAction.CONCURRENT_ACTIVE in actions


def test_6_non_exclusive_imports_concurrency_and_removal():
    """Verify that IMPORTS coexist concurrently and are closed only by explicit removal evidence."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(2)
    t3 = _dt(3)

    imp_numpy = TemporalCodeRelation(
        id="rel-imp-np",
        subject="apps/api/src/service.py",
        relation=RelationType.IMPORTS,
        object="numpy",
        t_start=t1,
        fingerprint="fp_imp_np",
    )

    imp_pandas = TemporalCodeRelation(
        id="rel-imp-pd",
        subject="apps/api/src/service.py",
        relation=RelationType.IMPORTS,
        object="pandas",
        t_start=t2,
        fingerprint="fp_imp_pd",
    )

    # Initial state: both numpy and pandas active
    step1 = engine.resolve_contradictions([imp_pandas], existing_relations=[imp_numpy])
    assert len(step1.active_relations) == 2

    # Removal event for numpy at t3
    imp_numpy_removal = TemporalCodeRelation(
        id="rel-rem-np",
        subject="apps/api/src/service.py",
        relation=RelationType.IMPORTS,
        object="numpy",
        t_start=None,
        t_end=t3,
        provenance={"change_type": "DELETE", "is_removal": True},
        fingerprint="fp_rem_np",
    )

    step2 = engine.resolve_contradictions([imp_numpy_removal], existing_relations=step1.all_relations)

    active_objs = [r.canonical_object for r in step2.active_relations]
    assert "pandas" in active_objs
    assert "numpy" not in active_objs

    # numpy is now in historical_relations closed at t3
    closed_np = next(r for r in step2.historical_relations if r.canonical_object == "numpy")
    assert closed_np.t_end == t3


def test_7_low_confidence_conflict_preservation():
    """Verify that a conflicting exclusive claim below 0.65 confidence is preserved as uncertain without superseding."""
    engine = EvoKGContradictionEngine(min_confidence_threshold=0.65)

    t1 = _dt(1)
    t2 = _dt(2)

    active_rel = TemporalCodeRelation(
        id="rel-active-price",
        subject="get_price",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="float",
        t_start=t1,
        confidence=FactConfidence.HIGH,
        confidence_score=0.95,
        fingerprint="fp_active_price",
    )

    # Incoming assertion has confidence 0.50 (< 0.65 threshold)
    weak_rel = TemporalCodeRelation(
        id="rel-weak-price",
        subject="get_price",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="Decimal",
        t_start=t2,
        confidence=FactConfidence.MEDIUM,
        confidence_score=0.50,
        fingerprint="fp_weak_price",
    )

    result = engine.resolve_contradictions([weak_rel], existing_relations=[active_rel])

    # Active assertion remains active and untouched!
    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-active-price"
    assert result.active_relations[0].t_end is None

    # Weak assertion is preserved as a conflict
    assert len(result.conflicting_relations) == 1
    conf_item = result.conflicting_relations[0]
    assert conf_item.id == "rel-weak-price"
    assert conf_item.is_uncertain is True
    assert conf_item.has_temporal_conflict is True
    assert conf_item.confidence == FactConfidence.UNCERTAIN

    diag = next(d for d in result.diagnostics if d.action == ResolutionAction.LOW_CONFIDENCE_CONFLICT)
    assert diag.target_relation_id == "rel-active-price"


def test_8_out_of_order_historical_insertion():
    """Verify that an out-of-order historical assertion (t_new < t_old) is inserted with bounded interval without closing active."""
    engine = EvoKGContradictionEngine()

    t_modern = _dt(5)
    t_legacy = _dt(2)

    # Active relation established at t=5
    active_rel = TemporalCodeRelation(
        id="rel-modern",
        subject="user_service::find_user",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="UserModel",
        t_start=t_modern,
        confidence_score=0.95,
        fingerprint="fp_modern",
    )

    # Out-of-order assertion from earlier commit at t=2
    historical_rel = TemporalCodeRelation(
        id="rel-legacy",
        subject="user_service::find_user",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="dict",
        t_start=t_legacy,
        confidence_score=0.95,
        fingerprint="fp_legacy",
    )

    result = engine.resolve_contradictions([historical_rel], existing_relations=[active_rel])

    # Active relation remains active
    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-modern"
    assert result.active_relations[0].t_end is None

    # Historical assertion is inserted with interval [t_legacy, t_modern]
    assert len(result.historical_relations) == 1
    h_item = result.historical_relations[0]
    assert h_item.id == "rel-legacy"
    assert h_item.t_start == t_legacy
    assert h_item.t_end == t_modern
    assert h_item.superseded_by_id == "rel-modern"

    diag = next(d for d in result.diagnostics if d.action == ResolutionAction.HISTORICAL_INSERTION)
    assert diag.target_relation_id == "rel-modern"


def test_9_same_object_idempotency():
    """Verify that re-asserting an identical relation is idempotent and merges provenance without duplication."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(3)

    rel1 = TemporalCodeRelation(
        id="rel-idem-1",
        subject="auth_service",
        relation=RelationType.CALLS,
        object="token_validator",
        t_start=t1,
        t_obs=t1,
        commit_sha="c111",
        history_commit_shas=["c111"],
        source_fact_id="fact-1",
        fingerprint="fp_idem",
    )

    rel2 = TemporalCodeRelation(
        id="rel-idem-2",
        subject="auth_service",
        relation=RelationType.CALLS,
        object="token_validator",
        t_start=t1,
        t_obs=t2,
        commit_sha="c222",
        history_commit_shas=["c222"],
        source_fact_id="fact-2",
        fingerprint="fp_idem",
    )

    result = engine.resolve_contradictions([rel2], existing_relations=[rel1])

    assert len(result.all_relations) == 1
    merged = result.all_relations[0]
    assert merged.id == "rel-idem-1"
    assert merged.t_obs == t2
    assert "c111" in merged.history_commit_shas
    assert "c222" in merged.history_commit_shas
    assert "fact-1" in merged.history_fact_ids
    assert "fact-2" in merged.history_fact_ids

    diag = next(d for d in result.diagnostics if d.action == ResolutionAction.IDEMPOTENT_NOOP)
    assert diag.target_relation_id == "rel-idem-1"


def test_10_different_scope_protection():
    """Verify that distinct lexical scopes protect independent variable type bindings from cross-supersession."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(2)

    var_block_a = TemporalCodeRelation(
        id="rel-var-a",
        subject="apps/api/src/math.py::calc::x",
        relation=RelationType.ASSIGNED_TYPE,
        object="int",
        scope_key="scope:block_a",
        t_start=t1,
        confidence_score=0.95,
        fingerprint="fp_var_a",
    )

    var_block_b = TemporalCodeRelation(
        id="rel-var-b",
        subject="apps/api/src/math.py::calc::x",
        relation=RelationType.ASSIGNED_TYPE,
        object="str",
        scope_key="scope:block_b",
        t_start=t2,
        confidence_score=0.95,
        fingerprint="fp_var_b",
    )

    result = engine.resolve_contradictions([var_block_b], existing_relations=[var_block_a])

    assert len(result.active_relations) == 2
    assert len(result.superseded_relations) == 0


def test_11_different_branch_isolation():
    """Verify that assertions on different branches remain isolated and do not terminate each other."""
    engine = EvoKGContradictionEngine()

    t1 = _dt(1)
    t2 = _dt(2)

    rel_main = TemporalCodeRelation(
        id="rel-branch-main",
        subject="get_status",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="str",
        t_start=t1,
        provenance={"branch": "main"},
        confidence_score=0.95,
        fingerprint="fp_b_main",
    )

    rel_feature = TemporalCodeRelation(
        id="rel-branch-feat",
        subject="get_status",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="StatusEnum",
        t_start=t2,
        provenance={"branch": "feature/status-enum"},
        confidence_score=0.95,
        fingerprint="fp_b_feat",
    )

    result = engine.resolve_contradictions([rel_feature], existing_relations=[rel_main])

    # Both relations remain active within their respective branch scopes!
    assert len(result.active_relations) == 2
    assert len(result.superseded_relations) == 0

    diag = next(d for d in result.diagnostics if d.action == ResolutionAction.BRANCH_ISOLATED)
    assert diag.target_relation_id == "rel-branch-main"


def test_12_commit_ancestry_validation():
    """Verify that parallel non-ancestor commits do not supersede each other even if wall-clock time is later."""
    # Commit DAG: c1 branches to parallel commits c2 and c3
    commit_parents = {
        "c2": ["c1"],
        "c3": ["c1"],
    }
    engine = EvoKGContradictionEngine(commit_parents=commit_parents)

    # c2 commit at t=10
    rel_c2 = TemporalCodeRelation(
        id="rel-c2",
        subject="config_loader",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="ConfigV2",
        commit_sha="c2",
        t_start=_dt(10),
        confidence_score=0.95,
        fingerprint="fp_c2",
    )

    # c3 commit at t=11 (later wall-clock time, but NOT a descendant of c2!)
    rel_c3 = TemporalCodeRelation(
        id="rel-c3",
        subject="config_loader",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="ConfigV3",
        commit_sha="c3",
        t_start=_dt(11),
        confidence_score=0.95,
        fingerprint="fp_c3",
    )

    # Verify is_ancestor directly
    assert engine.is_ancestor("c1", "c2") is True
    assert engine.is_ancestor("c1", "c3") is True
    assert engine.is_ancestor("c2", "c3") is False

    result = engine.resolve_contradictions([rel_c3], existing_relations=[rel_c2])

    # c2 is NOT superseded by c3!
    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-c2"

    # c3 is preserved as conflicting uncertain evidence
    assert len(result.conflicting_relations) == 1
    assert result.conflicting_relations[0].id == "rel-c3"
    assert result.conflicting_relations[0].has_temporal_conflict is True

    diag = next(d for d in result.diagnostics if d.action == ResolutionAction.ANCESTRY_DISCONNECTED)
    assert diag.target_relation_id == "rel-c2"


def test_13_merge_commit_handling():
    """Verify that a merge commit having both parent commits in its ancestry successfully resolves prior assertions."""
    # Commit DAG: c1 -> c2 and c3; merge_m merges c2 and c3
    commit_parents = {
        "c2": ["c1"],
        "c3": ["c1"],
        "merge_m": ["c2", "c3"],
    }
    engine = EvoKGContradictionEngine(commit_parents=commit_parents)

    rel_c2 = TemporalCodeRelation(
        id="rel-c2-premerge",
        subject="config_loader",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="ConfigV2",
        commit_sha="c2",
        provenance={"branch": "feature/v2"},
        t_start=_dt(10),
        confidence_score=0.95,
        fingerprint="fp_c2_pre",
    )

    # Merge commit on main
    rel_merge = TemporalCodeRelation(
        id="rel-merge-m",
        subject="config_loader",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="ConfigResolved",
        commit_sha="merge_m",
        provenance={"branch": "main"},
        t_start=_dt(15),
        confidence_score=0.95,
        fingerprint="fp_merge_res",
    )

    assert engine.is_ancestor("c2", "merge_m") is True
    assert engine.is_ancestor("c3", "merge_m") is True

    result = engine.resolve_contradictions([rel_merge], existing_relations=[rel_c2])

    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-merge-m"

    assert len(result.superseded_relations) == 1
    assert result.superseded_relations[0].id == "rel-c2-premerge"
    assert result.superseded_relations[0].superseded_by_id == "rel-merge-m"


def test_14_missing_timestamp_handling():
    """Verify that missing timestamps are handled conservatively without fabricating dates."""
    engine = EvoKGContradictionEngine()

    active_rel = TemporalCodeRelation(
        id="rel-known-ts",
        subject="calculate_tax",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="float",
        t_start=_dt(2),
        confidence_score=0.95,
        fingerprint="fp_known_ts",
    )

    # Missing start and obs time
    unanchored_rel = TemporalCodeRelation(
        id="rel-unanchored",
        subject="calculate_tax",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="Decimal",
        t_start=None,
        t_obs=None,
        confidence_score=0.95,
        fingerprint="fp_unanchored",
    )

    result = engine.resolve_contradictions([unanchored_rel], existing_relations=[active_rel])

    # Active relation remains active
    assert len(result.active_relations) == 1
    assert result.active_relations[0].id == "rel-known-ts"

    # Unanchored relation is retained as uncertain conflict without fabrication
    assert len(result.conflicting_relations) == 1
    assert result.conflicting_relations[0].id == "rel-unanchored"
    assert result.conflicting_relations[0].is_uncertain is True
    assert result.conflicting_relations[0].t_start is None


def test_15_invalid_temporal_interval_protection():
    """Verify that relations with t_end earlier than t_start are detected and flagged as conflicts."""
    engine = EvoKGContradictionEngine()

    t_start = _dt(5)
    t_end = _dt(2)  # t_end < t_start: invalid interval!

    invalid_rel = TemporalCodeRelation(
        id="rel-invalid-int",
        subject="process_data",
        relation=RelationType.CALLS,
        object="legacy_sink",
        t_start=t_start,
        t_end=t_end,
        fingerprint="fp_invalid_int",
    )

    result = engine.resolve_contradictions([invalid_rel])

    assert len(result.conflicting_relations) == 1
    assert result.conflicting_relations[0].has_temporal_conflict is True
    assert result.conflicting_relations[0].is_uncertain is True
    assert "Temporal conflict" in (result.conflicting_relations[0].conflict_detail or "")


def test_16_batch_processing_determinism():
    """Verify that batch resolution produces identical results regardless of input order."""
    engine = EvoKGContradictionEngine()

    # Sequence of 4 relations evolving over time
    r1 = TemporalCodeRelation(
        id="rel-seq-1",
        subject="api_service",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TypeA",
        t_start=_dt(1),
        confidence_score=0.95,
        fingerprint="fp_seq_1",
    )

    r2 = TemporalCodeRelation(
        id="rel-seq-2",
        subject="api_service",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TypeB",
        t_start=_dt(2),
        confidence_score=0.95,
        fingerprint="fp_seq_2",
    )

    r3 = TemporalCodeRelation(
        id="rel-seq-3",
        subject="api_service",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TypeC",
        t_start=_dt(3),
        confidence_score=0.95,
        fingerprint="fp_seq_3",
    )

    r_call = TemporalCodeRelation(
        id="rel-seq-call",
        subject="api_service",
        relation=RelationType.CALLS,
        object="db_service",
        t_start=_dt(2),
        fingerprint="fp_seq_call",
    )

    input_ordered = [r1, r2, r3, r_call]

    # Run in forward order
    res_forward = engine.resolve_contradictions(input_ordered)

    # Run in reverse order
    res_reverse = engine.resolve_contradictions(list(reversed(input_ordered)))

    # Run in random shuffled order
    shuffled = list(input_ordered)
    random.Random(42).shuffle(shuffled)
    res_shuffled = engine.resolve_contradictions(shuffled)

    # Active relations must be identical
    active_forward = {r.id: r.canonical_object for r in res_forward.active_relations}
    active_reverse = {r.id: r.canonical_object for r in res_reverse.active_relations}
    active_shuffled = {r.id: r.canonical_object for r in res_shuffled.active_relations}

    assert active_forward == {"rel-seq-3": "TypeC", "rel-seq-call": "db_service"}
    assert active_forward == active_reverse
    assert active_forward == active_shuffled

    # Superseded relations must be identical
    superseded_forward = {r.id: (r.t_end, r.superseded_by_id) for r in res_forward.superseded_relations}
    superseded_reverse = {r.id: (r.t_end, r.superseded_by_id) for r in res_reverse.superseded_relations}
    superseded_shuffled = {r.id: (r.t_end, r.superseded_by_id) for r in res_shuffled.superseded_relations}

    assert superseded_forward == superseded_reverse
    assert superseded_forward == superseded_shuffled
