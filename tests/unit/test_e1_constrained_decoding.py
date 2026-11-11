"""
Unit tests for E1 Constrained Decoding & Grammar FSM Engine (Phase 4).
Verifies schema grammar validation, error detection, repair simulation,
and comparative overhead measurements between M0, M1, and M2.
"""

from experiments.e1_generative_ie.constrained_decoding import (
    SchemaGrammarFSM,
    evaluate_structured_generation_comparison,
)


def test_schema_grammar_fsm_valid_payload():
    fsm = SchemaGrammarFSM()
    valid_json = """{
        "entities": [
            {"entity_name": "CalculatorService", "entity_type": "SERVICE", "file_path": "service.py"}
        ],
        "relations": [
            {"subject": "CalculatorService", "relation_type": "CALLS", "object": "compute"}
        ],
        "events": [
            {"event_type": "COMPONENT_MODIFIED", "target_component": "CalculatorService", "trigger_statement": "update"}
        ]
    }"""
    is_valid, msg, overhead = fsm.validate_stream_conformity(valid_json)
    assert is_valid is True
    assert "Conforms" in msg
    assert overhead >= 0.0


def test_schema_grammar_fsm_rejects_missing_keys_or_invalid_enums():
    fsm = SchemaGrammarFSM()

    # 1. Missing required 'file_path'
    missing_key = """{
        "entities": [
            {"entity_name": "CalculatorService", "entity_type": "SERVICE"}
        ]
    }"""
    is_valid1, msg1, _ = fsm.validate_stream_conformity(missing_key)
    assert is_valid1 is False
    assert "missing required keys" in msg1

    # 2. Invalid enum type
    invalid_enum = """{
        "entities": [
            {"entity_name": "CalculatorService", "entity_type": "MAGIC_UNIVERSE", "file_path": "s.py"}
        ]
    }"""
    is_valid2, msg2, _ = fsm.validate_stream_conformity(invalid_enum)
    assert is_valid2 is False
    assert "invalid entity_type" in msg2


def test_schema_grammar_fsm_constrain_and_repair():
    fsm = SchemaGrammarFSM()
    bad_payload = {
        "entities": [
            {"entity_name": "ValidService", "entity_type": "SERVICE", "file_path": "s.py"},
            {"entity_name": "BadTypeService", "entity_type": "NON_EXISTENT_TYPE"},
            {"missing_name": True},
        ],
        "relations": [
            {"subject": "ValidService", "relation_type": "CALLS", "object": "run"},
            {"subject": "BadRel", "relation_type": "TELEPORTS_TO", "object": "moon"},
        ],
        "events": [
            {"target_component": "ValidService", "event_type": "API_CHANGED"},
        ],
    }

    repaired, overhead = fsm.constrain_and_repair(bad_payload)
    assert len(repaired["entities"]) == 2  # Missing name skipped, invalid type mapped to OTHER
    assert repaired["entities"][1]["entity_type"] == "OTHER"
    assert len(repaired["relations"]) == 2  # Invalid relation type mapped to REFERENCES
    assert repaired["relations"][1]["relation_type"] == "REFERENCES"
    assert len(repaired["events"]) == 1
    assert overhead >= 0.0


def test_evaluate_structured_generation_comparison():
    sample_payloads = [
        '{"entities": [{"entity_name": "ServiceA", "entity_type": "SERVICE", "file_path": "a.py"}]}',
        '```json\n{"entities": [{"entity_name": "ServiceB", "entity_type": "SERVICE", "file_path": "b.py"}]}\n```',
        '{"entities": [{"entity_name": "ServiceC"}]}',  # missing file_path
    ]
    comparison = evaluate_structured_generation_comparison(sample_payloads)
    assert "M0_Deterministic_ATOM" in comparison
    assert "M1_Provider_JSON_Mode" in comparison
    assert "M2_Constrained_Decoding" in comparison

    m0 = comparison["M0_Deterministic_ATOM"]
    m1 = comparison["M1_Provider_JSON_Mode"]
    m2 = comparison["M2_Constrained_Decoding"]

    assert m0.schema_validity_rate == 1.0
    assert m1.schema_validity_rate >= 0.0
    assert m2.schema_validity_rate == 1.0
    assert m2.missing_fields_rate == 0.0
    assert m2.invalid_types_rate == 0.0
