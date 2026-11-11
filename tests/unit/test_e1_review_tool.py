"""
Unit tests for the E1 Human Review Tool (experiments/e1_generative_ie/review_tool.py).
Verifies workflow operations: inspect, approve, reject, edit, add, uncertainty flagging,
save/resume round-trip, and export summary.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

from experiments.e1_generative_ie.review_tool import E1ReviewSession


def test_review_session_load_and_counts():
    session = E1ReviewSession()
    assert len(session.cases) == 40
    summary = session.get_progress_summary()
    assert summary["total_cases"] == 40
    assert summary["reviewed_cases"] == 0
    assert summary["pending_review"] == 40
    assert summary["split_breakdown"] == {"dev": 20, "eval": 20}


def test_review_session_list_and_filter():
    session = E1ReviewSession()
    dev_cases = session.list_cases(split="dev")
    eval_cases = session.list_cases(split="eval")
    assert len(dev_cases) == 20
    assert len(eval_cases) == 20

    simple_cases = session.list_cases(category="Simple")
    assert len(simple_cases) == 1
    assert simple_cases[0]["case_id"] == "dev_01_simple_func_mod"


def test_review_session_format_display():
    session = E1ReviewSession()
    display = session.format_case_display("dev_01_simple_func_mod")
    assert "dev_01_simple_func_mod" in display
    assert "fix(calc): update score multiplier" in display
    assert "calculate_score" in display
    assert "BEHAVIOR_CHANGED" in display

    missing = session.format_case_display("non_existent_case_99")
    assert "Error: Case 'non_existent_case_99' not found." in missing


def test_review_session_approve_and_reject_workflow():
    with NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        session = E1ReviewSession()
        session.save(tmp_path)

        # Work on isolated temp file
        temp_session = E1ReviewSession(annotation_file=tmp_path)
        # Approve dev_01
        res = temp_session.approve_case("dev_01_simple_func_mod", reviewer="alice_dev", notes="Verified OK")
        assert res is True
        c = temp_session.get_case("dev_01_simple_func_mod")
        assert c["annotation_status"] == "HUMAN_VERIFIED"
        assert c["review_metadata"]["reviewed_by"] == "alice_dev"
        assert c["review_metadata"]["reviewer_notes"] == "Verified OK"

        # Reject dev_02
        res2 = temp_session.reject_case("dev_02_dependency_redis", reviewer="bob_dev", reason="Incorrect dependency type")
        assert res2 is True
        c2 = temp_session.get_case("dev_02_dependency_redis")
        assert c2["annotation_status"] == "REJECTED"
        assert c2["review_metadata"]["reviewed_by"] == "bob_dev"
        assert c2["review_metadata"]["reviewer_notes"] == "Incorrect dependency type"

        # Mark uncertain dev_03
        res3 = temp_session.mark_uncertain("dev_03_api_route_update", reviewer="carol_dev", notes="Need team consensus")
        assert res3 is True
        c3 = temp_session.get_case("dev_03_api_route_update")
        assert c3["annotation_status"] == "NEEDS_REVIEW"
        assert c3["is_ambiguous"] is True

        # Check progress summary
        summary = temp_session.get_progress_summary()
        assert summary["reviewed_cases"] == 2  # dev_01 and dev_02
        assert summary["pending_review"] == 38

        # Save and reload to verify persistence
        temp_session.save()
        reloaded = E1ReviewSession(annotation_file=tmp_path)
        assert reloaded.get_case("dev_01_simple_func_mod")["annotation_status"] == "HUMAN_VERIFIED"
        assert reloaded.get_case("dev_02_dependency_redis")["annotation_status"] == "REJECTED"
        assert reloaded.get_case("dev_03_api_route_update")["annotation_status"] == "NEEDS_REVIEW"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_review_session_edit_and_add_annotations():
    with NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        session = E1ReviewSession()
        session.save(tmp_path)

        temp_session = E1ReviewSession(annotation_file=tmp_path)
        case_id = "dev_01_simple_func_mod"

        # Add entity
        assert temp_session.add_entity(case_id, name="RankingEngine", entity_type="CLASS", evidence_span="RankingEngine") is True
        c = temp_session.get_case(case_id)
        assert any(e["name"] == "RankingEngine" for e in c["expected_entities"])

        # Edit entity
        assert temp_session.edit_entity(case_id, 0, name="calculate_custom_score") is True
        assert c["expected_entities"][0]["name"] == "calculate_custom_score"

        # Add relation
        assert temp_session.add_relation(case_id, subject="RankingEngine", rel="CALLS", obj="calculate_custom_score") is True
        assert any(r["subject"] == "RankingEngine" and r["obj"] == "calculate_custom_score" for r in c["expected_relations"])

        # Verify protection against empty reviewer
        assert temp_session.approve_case("dev_01_simple_func_mod", reviewer="") is False
        assert temp_session.reject_case("dev_02_dependency_redis", reviewer="", reason="empty") is False

        # Add event
        assert temp_session.add_event(case_id, event_type="API_CHANGED", target="calculate_custom_score", trigger_statement="update scoring signature") is True
        assert any(ev["type"] == "API_CHANGED" for ev in c["expected_events"])

        # Edit relation & event
        assert temp_session.edit_relation(case_id, 0, subject="RankingEngineV2") is True
        assert c["expected_relations"][0]["subject"] == "RankingEngineV2"
        assert temp_session.edit_event(case_id, 0, event_type="BEHAVIOR_CHANGED") is True
        assert c["expected_events"][0]["type"] == "BEHAVIOR_CHANGED"

        # Delete entity, relation, event
        ent_count_before = len(c["expected_entities"])
        assert temp_session.delete_entity(case_id, 0) is True
        assert len(c["expected_entities"]) == ent_count_before - 1

        rel_count_before = len(c["expected_relations"])
        assert temp_session.delete_relation(case_id, 0) is True
        assert len(c["expected_relations"]) == rel_count_before - 1

        ev_count_before = len(c["expected_events"])
        assert temp_session.delete_event(case_id, 0) is True
        assert len(c["expected_events"]) == ev_count_before - 1

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
