"""
Unit Tests for EvoKG Relation Taxonomy and Temporal Schemas (T2.1 Milestone).
Reference: arXiv:2509.15464 (EvoReasoner / EvoKG).
"""

from datetime import UTC, datetime

from apps.api.src.schemas.code_atom import (
    FactConfidence,
    PropertyExclusivity,
    RelationType,
    ScopeKeyStrategy,
    TemporalCodeRelation,
    TemporalSupersessionPolicy,
)
from apps.api.src.services.code_atom.relation_extractor import (
    generate_relation_fingerprint,
    normalize_relation_name,
)
from apps.api.src.services.code_atom.taxonomy import (
    CodeRelationTaxonomy,
    RelationTaxonomyEntry,
)


def test_1_all_existing_relation_types_classified():
    """Verify that every one of the original 9 RelationType values is explicitly classified."""
    original_relations = [
        RelationType.CALLS,
        RelationType.DEFINES,
        RelationType.IMPORTS,
        RelationType.INHERITS,
        RelationType.MUTATES,
        RelationType.CONFIGURES,
        RelationType.VALIDATES,
        RelationType.RAISES,
        RelationType.REFERENCES,
    ]

    for rel in original_relations:
        entry = CodeRelationTaxonomy.classify(rel)
        assert isinstance(entry, RelationTaxonomyEntry)
        assert entry.canonical_predicate == rel

    # Non-exclusive concurrent relations
    non_exclusive_rels = [
        RelationType.CALLS,
        RelationType.IMPORTS,
        RelationType.REFERENCES,
        RelationType.RAISES,
        RelationType.MUTATES,
        RelationType.CONFIGURES,
        RelationType.VALIDATES,
    ]
    for rel in non_exclusive_rels:
        entry = CodeRelationTaxonomy.classify(rel)
        assert entry.exclusivity == PropertyExclusivity.NON_EXCLUSIVE
        assert entry.supersession_policy == TemporalSupersessionPolicy.CONCURRENT
        assert not CodeRelationTaxonomy.is_exclusive(rel)

    # Exclusive relations
    assert CodeRelationTaxonomy.is_exclusive(RelationType.DEFINES)
    assert CodeRelationTaxonomy.classify(RelationType.DEFINES).supersession_policy == (
        TemporalSupersessionPolicy.CONTAINER_EXCLUSIVE
    )
    assert CodeRelationTaxonomy.is_exclusive(RelationType.INHERITS)
    assert CodeRelationTaxonomy.classify(RelationType.INHERITS).supersession_policy == (
        TemporalSupersessionPolicy.SLOT_EXCLUSIVE
    )


def test_2_all_new_relation_types_classified():
    """Verify that all approved EvoKG Code Lane extensions are classified properly."""
    new_relations = [
        (RelationType.DEFINES_RETURN_TYPE, ScopeKeyStrategy.OVERLOAD_INDEX, TemporalSupersessionPolicy.SLOT_EXCLUSIVE),
        (RelationType.HAS_SIGNATURE, ScopeKeyStrategy.OVERLOAD_INDEX, TemporalSupersessionPolicy.SLOT_EXCLUSIVE),
        (RelationType.ASSIGNED_TYPE, ScopeKeyStrategy.LEXICAL_SCOPE, TemporalSupersessionPolicy.SLOT_EXCLUSIVE),
        (RelationType.MODULE_LOCATION, ScopeKeyStrategy.CANONICAL_PATH, TemporalSupersessionPolicy.PATH_EXCLUSIVE),
    ]

    for rel, expected_strategy, expected_policy in new_relations:
        assert CodeRelationTaxonomy.is_exclusive(rel)
        entry = CodeRelationTaxonomy.classify(rel)
        assert entry.exclusivity == PropertyExclusivity.EXCLUSIVE
        assert entry.scope_strategy == expected_strategy
        assert entry.supersession_policy == expected_policy
        assert entry.canonical_predicate == rel


def test_3_relation_aliases_normalize_correctly():
    """Verify that aliases resolve to their canonical predicate without creating duplicate predicates."""
    aliases_to_expected = {
        # Inheritance aliases
        "EXTENDS_CLASS": RelationType.INHERITS,
        "extends": RelationType.INHERITS,
        "subclass_of": RelationType.INHERITS,
        "implements": RelationType.INHERITS,
        "base": RelationType.INHERITS,
        # Call aliases
        "invokes": RelationType.CALLS,
        "call": RelationType.CALLS,
        "calls_method": RelationType.CALLS,
        "dispatch": RelationType.CALLS,
        # Import aliases
        "require": RelationType.IMPORTS,
        "include": RelationType.IMPORTS,
        # Return type & signature aliases
        "returns": RelationType.DEFINES_RETURN_TYPE,
        "return_type": RelationType.DEFINES_RETURN_TYPE,
        "defines_return": RelationType.DEFINES_RETURN_TYPE,
        "signature": RelationType.HAS_SIGNATURE,
        "parameters": RelationType.HAS_SIGNATURE,
        "params": RelationType.HAS_SIGNATURE,
        # Type & location aliases
        "type_annotation": RelationType.ASSIGNED_TYPE,
        "variable_type": RelationType.ASSIGNED_TYPE,
        "file_location": RelationType.MODULE_LOCATION,
        "located_in": RelationType.MODULE_LOCATION,
    }

    for alias, expected_canon in aliases_to_expected.items():
        assert normalize_relation_name(alias) == expected_canon
        assert CodeRelationTaxonomy.get_canonical_predicate(alias) == expected_canon
        # Alias classification matches canonical classification
        alias_entry = CodeRelationTaxonomy.classify(alias)
        canon_entry = CodeRelationTaxonomy.classify(expected_canon)
        assert alias_entry.exclusivity == canon_entry.exclusivity
        assert alias_entry.supersession_policy == canon_entry.supersession_policy


def test_4_unknown_predicates_default_non_exclusive_and_uncertain():
    """Verify that unknown/unclassified relationships default to non-exclusive and uncertain."""
    unknown_rel = "CUSTOM_ARBITRARY_EDGE"

    entry = CodeRelationTaxonomy.classify(unknown_rel)
    assert entry.exclusivity == PropertyExclusivity.NON_EXCLUSIVE
    assert entry.canonical_predicate == RelationType.REFERENCES
    assert entry.scope_strategy == ScopeKeyStrategy.UNCERTAIN
    assert entry.supersession_policy == TemporalSupersessionPolicy.PRESERVE_UNCERTAIN
    assert not CodeRelationTaxonomy.is_exclusive(unknown_rel)

    # Instantiating a TemporalCodeRelation with unknown predicate
    rel_inst = TemporalCodeRelation(
        id="rel-test-unknown",
        subject="service_a",
        relation=unknown_rel,
        object="service_b",
        fingerprint="fp_unknown_1",
    )
    assert not rel_inst.is_exclusive
    assert rel_inst.is_uncertain is True
    assert rel_inst.confidence == FactConfidence.UNCERTAIN
    assert rel_inst.confidence_score <= 0.35
    assert rel_inst.scope_key == "unknown"


def test_5_python_multiple_inheritance_uses_separate_slots():
    """Verify that Python multiple inheritance uses distinct base slots that do not collide."""
    # Base 0 and Base 1
    key_base0, unc0 = CodeRelationTaxonomy.generate_scope_key(RelationType.INHERITS, slot_index=0)
    key_base1, unc1 = CodeRelationTaxonomy.generate_scope_key(RelationType.INHERITS, slot_index=1)

    assert key_base0 == "base:0"
    assert key_base1 == "base:1"
    assert not unc0
    assert not unc1

    # Same slot can supersede itself
    assert CodeRelationTaxonomy.can_supersede(RelationType.INHERITS, "base:0", RelationType.INHERITS, "base:0")
    assert CodeRelationTaxonomy.can_supersede(RelationType.INHERITS, "base:1", RelationType.INHERITS, "base:1")

    # Distinct inheritance slots NEVER supersede each other
    assert not CodeRelationTaxonomy.can_supersede(RelationType.INHERITS, "base:0", RelationType.INHERITS, "base:1")
    assert not CodeRelationTaxonomy.can_supersede(RelationType.INHERITS, "base:1", RelationType.INHERITS, "base:0")

    # Aliases like EXTENDS_CLASS also map to the same slot policy
    assert CodeRelationTaxonomy.can_supersede("EXTENDS_CLASS", "base:0", RelationType.INHERITS, "base:0")


def test_6_overload_signatures_use_independent_scope_keys():
    """Verify that overloaded signatures use independent scope keys without cross-supersession."""
    key_ov0, unc0 = CodeRelationTaxonomy.generate_scope_key(RelationType.DEFINES_RETURN_TYPE, overload_index=0)
    key_ov1, unc1 = CodeRelationTaxonomy.generate_scope_key(RelationType.DEFINES_RETURN_TYPE, overload_index=1)

    assert key_ov0 == "overload:0"
    assert key_ov1 == "overload:1"
    assert not unc0
    assert not unc1

    # Same overload slot can supersede
    assert CodeRelationTaxonomy.can_supersede(
        RelationType.DEFINES_RETURN_TYPE, "overload:0", RelationType.DEFINES_RETURN_TYPE, "overload:0"
    )

    # Different overload slots do not collide or supersede
    assert not CodeRelationTaxonomy.can_supersede(
        RelationType.DEFINES_RETURN_TYPE, "overload:0", RelationType.DEFINES_RETURN_TYPE, "overload:1"
    )

    # HAS_SIGNATURE works identically
    assert CodeRelationTaxonomy.can_supersede(
        RelationType.HAS_SIGNATURE, "overload:1", RelationType.HAS_SIGNATURE, "overload:1"
    )
    assert not CodeRelationTaxonomy.can_supersede(
        RelationType.HAS_SIGNATURE, "overload:0", RelationType.HAS_SIGNATURE, "overload:1"
    )


def test_7_variable_type_assignments_scoped_correctly():
    """Verify that variable type assignments are scoped per lexical scope and handle missing scope conservatively."""
    key_scope_a, unc_a = CodeRelationTaxonomy.generate_scope_key(RelationType.ASSIGNED_TYPE, scope_id="fn_auth_body")
    key_scope_b, unc_b = CodeRelationTaxonomy.generate_scope_key(RelationType.ASSIGNED_TYPE, scope_id="fn_other_body")

    assert key_scope_a == "scope:fn_auth_body"
    assert key_scope_b == "scope:fn_other_body"
    assert not unc_a
    assert not unc_b

    # Different lexical scopes do not supersede
    assert not CodeRelationTaxonomy.can_supersede(
        RelationType.ASSIGNED_TYPE, "scope:fn_auth_body", RelationType.ASSIGNED_TYPE, "scope:fn_other_body"
    )

    # Missing scope information cannot be guessed: must flag uncertainty
    key_missing, unc_missing = CodeRelationTaxonomy.generate_scope_key(RelationType.ASSIGNED_TYPE, scope_id=None)
    assert key_missing == "scope:unspecified"
    assert unc_missing is True

    # Unspecified scope never causes supersession
    assert not CodeRelationTaxonomy.can_supersede(
        RelationType.ASSIGNED_TYPE, "scope:unspecified", RelationType.ASSIGNED_TYPE, "scope:unspecified"
    )


def test_8_same_scope_and_same_exclusive_property_map_consistently():
    """Verify that identical exclusive properties within the same scope map consistently."""
    rel = RelationType.DEFINES_RETURN_TYPE
    scope = "overload:0"

    assert CodeRelationTaxonomy.can_supersede(rel, scope, rel, scope)

    # Scoped fingerprints incorporate scope_key to distinguish overloads
    fp0 = generate_relation_fingerprint(
        commit_sha="c1",
        file_path="src/app.py",
        subject="get_data",
        relation=RelationType.DEFINES_RETURN_TYPE,
        target_object="dict",
        scope_key="overload:0",
    )
    fp1 = generate_relation_fingerprint(
        commit_sha="c1",
        file_path="src/app.py",
        subject="get_data",
        relation=RelationType.DEFINES_RETURN_TYPE,
        target_object="dict",
        scope_key="overload:1",
    )
    assert fp0 != fp1

    # Fingerprint without scope_key defaults cleanly
    fp_default = generate_relation_fingerprint(
        commit_sha="c1",
        file_path="src/app.py",
        subject="get_data",
        relation=RelationType.DEFINES_RETURN_TYPE,
        target_object="dict",
        scope_key=None,
    )
    assert len(fp_default) == 64


def test_9_different_scopes_never_collide():
    """Verify that distinct scopes, predicates, or non-exclusive relations never supersede."""
    # Different predicates cannot supersede
    assert not CodeRelationTaxonomy.can_supersede(
        RelationType.DEFINES_RETURN_TYPE, "overload:0", RelationType.HAS_SIGNATURE, "overload:0"
    )

    # Non-exclusive relations never supersede peers
    assert not CodeRelationTaxonomy.can_supersede(RelationType.CALLS, "concurrent", RelationType.CALLS, "concurrent")
    assert not CodeRelationTaxonomy.can_supersede(
        RelationType.IMPORTS, "concurrent", RelationType.IMPORTS, "concurrent"
    )

    # Symbol definition with different simple names do not collide
    assert not CodeRelationTaxonomy.can_supersede(RelationType.DEFINES, "symbol:login", RelationType.DEFINES, "symbol:logout")
    assert CodeRelationTaxonomy.can_supersede(RelationType.DEFINES, "symbol:login", RelationType.DEFINES, "symbol:login")


def test_10_temporal_code_relation_backward_compatibility_and_confidence():
    """Verify that TemporalCodeRelation maintains full backward compatibility with ATOM while validating EvoKG confidence."""
    now = datetime.now(UTC)

    # Standard ATOM creation retains default confidence without perturbation
    atom_rel = TemporalCodeRelation(
        id="rel-atom-1",
        subject="order_processor",
        relation=RelationType.CALLS,
        object="inventory_service",
        t_start=now,
        confidence=FactConfidence.HIGH,
        is_uncertain=False,
        fingerprint="fp_atom_1",
    )
    assert atom_rel.is_exclusive is False
    assert atom_rel.scope_key == "concurrent"
    assert atom_rel.confidence == FactConfidence.HIGH
    assert atom_rel.is_uncertain is False
    assert atom_rel.confidence_score == 0.95

    # Exclusive return type automatically sets exclusivity and default overload scope
    return_rel = TemporalCodeRelation(
        id="rel-ret-1",
        subject="get_user",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="UserDTO",
        fingerprint="fp_ret_1",
    )
    assert return_rel.is_exclusive is True
    assert return_rel.scope_key == "overload:0"
    assert return_rel.confidence == FactConfidence.HIGH
    assert return_rel.confidence_score == 0.95

    # Inconsistent combination: is_uncertain=True forces FactConfidence.UNCERTAIN
    inconsistent_rel = TemporalCodeRelation(
        id="rel-incon-1",
        subject="calc_tax",
        relation=RelationType.CALLS,
        object="tax_service",
        confidence=FactConfidence.HIGH,
        is_uncertain=True,
        fingerprint="fp_incon_1",
    )
    assert inconsistent_rel.is_uncertain is True
    assert inconsistent_rel.confidence == FactConfidence.UNCERTAIN
    assert inconsistent_rel.confidence_score <= 0.35

    # Explicit custom confidence score is preserved
    custom_conf_rel = TemporalCodeRelation(
        id="rel-custom-1",
        subject="calc_tax",
        relation=RelationType.CALLS,
        object="tax_service",
        confidence=FactConfidence.MEDIUM,
        confidence_score=0.78,
        fingerprint="fp_custom_1",
    )
    assert custom_conf_rel.confidence_score == 0.78
    assert custom_conf_rel.confidence == FactConfidence.MEDIUM

    # Serialization test
    dumped = custom_conf_rel.model_dump()
    assert dumped["is_exclusive"] is False
    assert dumped["scope_key"] == "concurrent"
    assert dumped["confidence_score"] == 0.78
    assert "superseded_by_id" in dumped
