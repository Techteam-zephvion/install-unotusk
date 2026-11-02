"""
Code Lane Relation Taxonomy and Exclusivity Policy Engine for EvoKG.
Reference: arXiv:2509.15464 (EvoReasoner / EvoKG: Temporal Reasoning with LLMs Augmented by Evolving KGs).

Provides:
1. Strict classification of relations into EXCLUSIVE vs NON_EXCLUSIVE.
2. Parameterized scope keys for overloads, multiple inheritance slots, lexical scopes, and symbol containers.
3. Deterministic canonical predicate mapping preserving all existing RelationType values.
4. Formal temporal supersession structural gating.
"""

from dataclasses import dataclass

from apps.api.src.schemas.code_atom import (
    PropertyExclusivity,
    RelationType,
    ScopeKeyStrategy,
    TemporalSupersessionPolicy,
)


@dataclass(frozen=True)
class RelationTaxonomyEntry:
    """Taxonomy specification for a code relationship predicate."""

    predicate: RelationType | str
    canonical_predicate: RelationType
    exclusivity: PropertyExclusivity
    scope_strategy: ScopeKeyStrategy
    supersession_policy: TemporalSupersessionPolicy
    description: str


class CodeRelationTaxonomy:
    """
    Centralized relation taxonomy and exclusivity policy engine.
    (arXiv:2509.15464 §3.1-3.2)
    """

    _TAXONOMY: dict[RelationType, RelationTaxonomyEntry] = {
        RelationType.CALLS: RelationTaxonomyEntry(
            predicate=RelationType.CALLS,
            canonical_predicate=RelationType.CALLS,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="Function or method call invocation. Supports multiple concurrent call targets.",
        ),
        RelationType.IMPORTS: RelationTaxonomyEntry(
            predicate=RelationType.IMPORTS,
            canonical_predicate=RelationType.IMPORTS,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="Module or package dependency import. Supports multiple concurrent imports.",
        ),
        RelationType.REFERENCES: RelationTaxonomyEntry(
            predicate=RelationType.REFERENCES,
            canonical_predicate=RelationType.REFERENCES,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="Symbol reference, variable lookup or type usage. Supports multiple concurrent targets.",
        ),
        RelationType.RAISES: RelationTaxonomyEntry(
            predicate=RelationType.RAISES,
            canonical_predicate=RelationType.RAISES,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="Exception raise, throw or error emission. Supports multiple concurrent exception types.",
        ),
        RelationType.MUTATES: RelationTaxonomyEntry(
            predicate=RelationType.MUTATES,
            canonical_predicate=RelationType.MUTATES,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="State mutation or variable modification. Supports multiple concurrent targets.",
        ),
        RelationType.CONFIGURES: RelationTaxonomyEntry(
            predicate=RelationType.CONFIGURES,
            canonical_predicate=RelationType.CONFIGURES,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="Configuration or setting parameter binding. Supports multiple concurrent settings.",
        ),
        RelationType.VALIDATES: RelationTaxonomyEntry(
            predicate=RelationType.VALIDATES,
            canonical_predicate=RelationType.VALIDATES,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CONCURRENT,
            supersession_policy=TemporalSupersessionPolicy.CONCURRENT,
            description="Assertion, schema validation or precondition check. Supports multiple concurrent validations.",
        ),
        RelationType.DEFINES: RelationTaxonomyEntry(
            predicate=RelationType.DEFINES,
            canonical_predicate=RelationType.DEFINES,
            exclusivity=PropertyExclusivity.EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.SYMBOL_NAME,
            supersession_policy=TemporalSupersessionPolicy.CONTAINER_EXCLUSIVE,
            description="Symbol definition inside a container. Exclusive per simple symbol name within container.",
        ),
        RelationType.DEFINES_RETURN_TYPE: RelationTaxonomyEntry(
            predicate=RelationType.DEFINES_RETURN_TYPE,
            canonical_predicate=RelationType.DEFINES_RETURN_TYPE,
            exclusivity=PropertyExclusivity.EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.OVERLOAD_INDEX,
            supersession_policy=TemporalSupersessionPolicy.SLOT_EXCLUSIVE,
            description="Return type annotation. Exclusive per overload signature index.",
        ),
        RelationType.HAS_SIGNATURE: RelationTaxonomyEntry(
            predicate=RelationType.HAS_SIGNATURE,
            canonical_predicate=RelationType.HAS_SIGNATURE,
            exclusivity=PropertyExclusivity.EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.OVERLOAD_INDEX,
            supersession_policy=TemporalSupersessionPolicy.SLOT_EXCLUSIVE,
            description="Function/method parameter signature. Exclusive per overload signature index.",
        ),
        RelationType.ASSIGNED_TYPE: RelationTaxonomyEntry(
            predicate=RelationType.ASSIGNED_TYPE,
            canonical_predicate=RelationType.ASSIGNED_TYPE,
            exclusivity=PropertyExclusivity.EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.LEXICAL_SCOPE,
            supersession_policy=TemporalSupersessionPolicy.SLOT_EXCLUSIVE,
            description="Variable or constant type assignment. Exclusive per variable within lexical scope.",
        ),
        RelationType.MODULE_LOCATION: RelationTaxonomyEntry(
            predicate=RelationType.MODULE_LOCATION,
            canonical_predicate=RelationType.MODULE_LOCATION,
            exclusivity=PropertyExclusivity.EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.CANONICAL_PATH,
            supersession_policy=TemporalSupersessionPolicy.PATH_EXCLUSIVE,
            description="Canonical module or file path of a code entity. Exclusive per symbol location.",
        ),
        RelationType.INHERITS: RelationTaxonomyEntry(
            predicate=RelationType.INHERITS,
            canonical_predicate=RelationType.INHERITS,
            exclusivity=PropertyExclusivity.EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.INHERITANCE_SLOT,
            supersession_policy=TemporalSupersessionPolicy.SLOT_EXCLUSIVE,
            description="Base class inheritance or interface implementation. Exclusive per base slot (base:0, base:1) to support multiple inheritance.",
        ),
    }

    _ALIAS_MAP: dict[str, RelationType] = {
        # Inheritance & subtyping aliases
        "EXTENDS_CLASS": RelationType.INHERITS,
        "EXTENDS": RelationType.INHERITS,
        "SUBCLASS": RelationType.INHERITS,
        "SUBCLASS_OF": RelationType.INHERITS,
        "BASE": RelationType.INHERITS,
        "IMPLEMENTS": RelationType.INHERITS,
        # Call aliases
        "INVOKES": RelationType.CALLS,
        "CALL": RelationType.CALLS,
        "CALLS_FUNCTION": RelationType.CALLS,
        "CALLS_METHOD": RelationType.CALLS,
        "DISPATCH": RelationType.CALLS,
        "DISPATCHES": RelationType.CALLS,
        # Import aliases
        "IMPORT": RelationType.IMPORTS,
        "IMPORTS_MODULE": RelationType.IMPORTS,
        "REQUIRE": RelationType.IMPORTS,
        "REQUIRES": RelationType.IMPORTS,
        "INCLUDE": RelationType.IMPORTS,
        # Definition aliases
        "DECLARE": RelationType.DEFINES,
        "DECLARES": RelationType.DEFINES,
        "IMPLEMENT": RelationType.DEFINES,
        # Type & signature aliases
        "RETURNS": RelationType.DEFINES_RETURN_TYPE,
        "RETURN_TYPE": RelationType.DEFINES_RETURN_TYPE,
        "RETURNS_TYPE": RelationType.DEFINES_RETURN_TYPE,
        "DEFINES_RETURN": RelationType.DEFINES_RETURN_TYPE,
        "SIGNATURE": RelationType.HAS_SIGNATURE,
        "PARAMETERS": RelationType.HAS_SIGNATURE,
        "PARAMS": RelationType.HAS_SIGNATURE,
        "TYPE_ANNOTATION": RelationType.ASSIGNED_TYPE,
        "VARIABLE_TYPE": RelationType.ASSIGNED_TYPE,
        "TYPED_AS": RelationType.ASSIGNED_TYPE,
        # Location aliases
        "FILE_LOCATION": RelationType.MODULE_LOCATION,
        "LOCATED_IN": RelationType.MODULE_LOCATION,
        "PATH": RelationType.MODULE_LOCATION,
        # Mutation aliases
        "MUTATE": RelationType.MUTATES,
        "MUTATING": RelationType.MUTATES,
        "MODIFIES": RelationType.MUTATES,
        # Config & validation aliases
        "CONFIG": RelationType.CONFIGURES,
        "SETTING": RelationType.CONFIGURES,
        "ENV": RelationType.CONFIGURES,
        "VALIDATE": RelationType.VALIDATES,
        "CHECKS": RelationType.VALIDATES,
        "VERIFIES": RelationType.VALIDATES,
        "GUARDS": RelationType.VALIDATES,
        # Exception aliases
        "RAISE": RelationType.RAISES,
        "THROW": RelationType.RAISES,
        "THROWS": RelationType.RAISES,
        "ERROR": RelationType.RAISES,
        "EXCEPT": RelationType.RAISES,
    }

    @classmethod
    def normalize_predicate(cls, relation: RelationType | str) -> RelationType | None:
        """
        Normalizes any relation representation or alias into its canonical RelationType.
        Returns None if relation is unclassified.
        """
        if isinstance(relation, RelationType):
            return relation

        if not relation or not str(relation).strip():
            return None

        clean = str(relation).strip().upper()
        if clean in RelationType.__members__:
            return RelationType[clean]

        if clean in cls._ALIAS_MAP:
            return cls._ALIAS_MAP[clean]

        clean_lower = clean.lower()
        if any(k in clean_lower for k in ("return_type", "defines_return", "returns_type", "return_val")):
            return RelationType.DEFINES_RETURN_TYPE
        if any(k in clean_lower for k in ("signature", "has_signature", "parameters", "params_spec")):
            return RelationType.HAS_SIGNATURE
        if any(k in clean_lower for k in ("assigned_type", "type_annotation", "variable_type")):
            return RelationType.ASSIGNED_TYPE
        if any(k in clean_lower for k in ("module_location", "file_location", "located_in")):
            return RelationType.MODULE_LOCATION
        if any(k in clean_lower for k in ("inherit", "extend", "subclass", "base")):
            return RelationType.INHERITS
        if any(k in clean_lower for k in ("call", "invoke", "dispatch")):
            return RelationType.CALLS
        if any(k in clean_lower for k in ("import", "require", "include")):
            return RelationType.IMPORTS
        if any(k in clean_lower for k in ("define", "declare", "implement")):
            return RelationType.DEFINES
        if any(k in clean_lower for k in ("mutate", "update", "set_", "modify", "touch")):
            return RelationType.MUTATES
        if any(k in clean_lower for k in ("config", "setting", "env")):
            return RelationType.CONFIGURES
        if any(k in clean_lower for k in ("validat", "check", "verify", "guard")):
            return RelationType.VALIDATES
        if any(k in clean_lower for k in ("raise", "throw", "error", "except")):
            return RelationType.RAISES

        return None

    @classmethod
    def classify(cls, relation: RelationType | str) -> RelationTaxonomyEntry:
        """
        Retrieves the authoritative taxonomy entry for a relation.
        Unknown or unclassified predicates default to NON_EXCLUSIVE, UNCERTAIN strategy,
        and PRESERVE_UNCERTAIN supersession policy.
        """
        canon = cls.normalize_predicate(relation)
        if canon is not None and canon in cls._TAXONOMY:
            return cls._TAXONOMY[canon]

        raw_str = relation.value if isinstance(relation, RelationType) else str(relation)
        return RelationTaxonomyEntry(
            predicate=raw_str,
            canonical_predicate=RelationType.REFERENCES,
            exclusivity=PropertyExclusivity.NON_EXCLUSIVE,
            scope_strategy=ScopeKeyStrategy.UNCERTAIN,
            supersession_policy=TemporalSupersessionPolicy.PRESERVE_UNCERTAIN,
            description=f"Unclassified relationship '{raw_str}'. Conservatively defaulted to non-exclusive and uncertain.",
        )

    @classmethod
    def is_exclusive(cls, relation: RelationType | str) -> bool:
        """Returns True if the relation is strictly exclusive in its scope slot."""
        return cls.classify(relation).exclusivity == PropertyExclusivity.EXCLUSIVE

    @classmethod
    def get_canonical_predicate(cls, relation: RelationType | str) -> RelationType:
        """Returns canonical RelationType enum for any predicate or alias."""
        return cls.classify(relation).canonical_predicate

    @classmethod
    def generate_scope_key(
        cls,
        relation: RelationType | str,
        *,
        symbol_name: str | None = None,
        overload_index: int | str | None = None,
        scope_id: str | None = None,
        slot_index: int | str | None = None,
        file_path: str | None = None,
        is_ambiguous: bool = False,
    ) -> tuple[str, bool]:
        """
        Generates a deterministic scope key for a relation assertion.

        Returns:
            tuple[str, bool]: (scope_key, requires_uncertainty)
            If scope cannot be established reliably, returns a safe fallback key
            and requires_uncertainty=True so that the relationship is preserved
            without terminating an unrelated assertion.
        """
        if is_ambiguous:
            return "uncertain:ambiguous", True

        entry = cls.classify(relation)
        strategy = entry.scope_strategy

        if strategy == ScopeKeyStrategy.OVERLOAD_INDEX:
            if overload_index is not None:
                try:
                    idx = int(overload_index)
                    if idx < 0:
                        return "overload:invalid", True
                    return f"overload:{idx}", False
                except (ValueError, TypeError):
                    clean = str(overload_index).strip()
                    if clean:
                        return f"overload:{clean}", False
                    return "overload:invalid", True
            return "overload:0", False

        elif strategy == ScopeKeyStrategy.LEXICAL_SCOPE:
            if scope_id is not None and str(scope_id).strip():
                clean_id = str(scope_id).strip()
                return f"scope:{clean_id}", False
            # Do not guess scope identities: mark uncertain
            return "scope:unspecified", True

        elif strategy == ScopeKeyStrategy.INHERITANCE_SLOT:
            if slot_index is not None:
                try:
                    s_idx = int(slot_index)
                    if s_idx < 0:
                        return "base:invalid", True
                    return f"base:{s_idx}", False
                except (ValueError, TypeError):
                    clean = str(slot_index).strip()
                    if clean:
                        return f"base:{clean}", False
                    return "base:invalid", True
            return "base:0", False

        elif strategy == ScopeKeyStrategy.SYMBOL_NAME:
            if symbol_name is not None and str(symbol_name).strip():
                s = str(symbol_name).strip()
                simple = s.split("::")[-1].split(".")[-1]
                if simple:
                    return f"symbol:{simple}", False
            return "symbol:unspecified", True

        elif strategy == ScopeKeyStrategy.CANONICAL_PATH:
            return "canonical_path", False

        elif strategy == ScopeKeyStrategy.CONCURRENT:
            return "concurrent", False

        # ScopeKeyStrategy.UNCERTAIN or fallback
        return "unknown", True

    @classmethod
    def build_scope_key(
        cls,
        relation: RelationType | str,
        *,
        symbol_name: str | None = None,
        overload_index: int | str | None = None,
        scope_id: str | None = None,
        slot_index: int | str | None = None,
        file_path: str | None = None,
        is_ambiguous: bool = False,
    ) -> str:
        """Convenience method returning string scope key directly."""
        key, _ = cls.generate_scope_key(
            relation,
            symbol_name=symbol_name,
            overload_index=overload_index,
            scope_id=scope_id,
            slot_index=slot_index,
            file_path=file_path,
            is_ambiguous=is_ambiguous,
        )
        return key

    @classmethod
    def can_supersede(
        cls,
        rel_a: RelationType | str,
        scope_key_a: str,
        rel_b: RelationType | str,
        scope_key_b: str,
    ) -> bool:
        """
        Determines whether assertion B has the structural potential to supersede assertion A.
        Both must be exclusive, map to the same canonical predicate, and share the same valid scope_key.
        """
        entry_a = cls.classify(rel_a)
        entry_b = cls.classify(rel_b)

        if (
            entry_a.exclusivity != PropertyExclusivity.EXCLUSIVE
            or entry_b.exclusivity != PropertyExclusivity.EXCLUSIVE
        ):
            return False

        if entry_a.canonical_predicate != entry_b.canonical_predicate:
            return False

        # Empty or uncertain scope keys must never cause supersession
        if (
            not scope_key_a
            or not scope_key_b
            or "unspecified" in scope_key_a
            or "unspecified" in scope_key_b
            or "unknown" in scope_key_a
            or "unknown" in scope_key_b
            or "invalid" in scope_key_a
            or "invalid" in scope_key_b
            or "ambiguous" in scope_key_a
            or "ambiguous" in scope_key_b
        ):
            return False

        return scope_key_a == scope_key_b
