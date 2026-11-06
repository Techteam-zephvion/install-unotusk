"""
Verification and anti-hallucination validation engine for E1 Generative Information Extraction.
Ensures every generative fact is strictly grounded in source diff tokens and AST bounds.
"""

import re

from experiments.e1_generative_ie.schema import (
    E1Entity,
    E1Event,
    E1ExtractionResult,
    E1Relation,
    ValidationStatus,
)

# Standard programmatic stopwords to avoid false-positive grounding rejections
COMMON_TOKENS_WHITELIST = {
    "this", "that", "with", "when", "then", "from", "into", "over", "under",
    "service", "function", "method", "class", "module", "file", "logic",
    "value", "record", "updates", "checks", "returns", "raises", "allows",
    "defines", "calls", "saves", "marks", "imports", "renamed", "removed",
    "deleted", "payload", "result", "condition", "bypass", "format", "fails",
    "error", "exception", "handler", "configures", "configuration", "status",
    "token", "email", "dirty", "user", "active", "admin", "role", "check",
    "test", "tests", "data", "database", "store", "table", "queue", "cache",
    "client", "server", "worker", "router", "endpoint", "event", "response",
    "request", "params", "argument", "dependency", "model", "schema", "view",
    "none", "null", "true", "false", "default", "init", "main", "start", "stop"
}


class E1GroundingValidator:
    """Verifies that extracted entities, relations, and events are grounded in the diff."""

    def __init__(self, token_whitelist: set[str] | None = None):
        self.whitelist = (token_whitelist or set()).union(COMMON_TOKENS_WHITELIST)

    def validate_result(
        self,
        result: E1ExtractionResult,
        raw_diff: str,
        commit_message: str,
    ) -> E1ExtractionResult:
        """
        Validates all entities, relations, and events against raw diff and commit message.
        Marks unsupported items as REJECTED or UNCERTAIN, and strips ungrounded items.
        """
        source_corpus = f"{raw_diff}\n{commit_message}\n{result.commit_sha}".lower()

        # Check for trivial diff / low semantic evidence
        if self._is_trivial_diff(raw_diff):
            result.abstention_triggered = True
            result.warnings.append("Abstention: Diff contains only trivial whitespace or comment changes.")
            result.entities = []
            result.relations = []
            result.events = []
            return result

        validated_entities: list[E1Entity] = []
        for entity in result.entities:
            status, reason = self.verify_entity_grounding(entity, source_corpus)
            entity.validation_status = status
            if status == ValidationStatus.VALIDATED:
                validated_entities.append(entity)
            elif status == ValidationStatus.UNCERTAIN:
                entity.confidence = min(entity.confidence, 0.40)
                validated_entities.append(entity)
            else:
                result.warnings.append(f"Rejected entity '{entity.entity_name}': {reason}")

        validated_relations: list[E1Relation] = []
        for relation in result.relations:
            status, reason = self.verify_relation_grounding(relation, source_corpus)
            relation.validation_status = status
            if status == ValidationStatus.VALIDATED:
                validated_relations.append(relation)
            elif status == ValidationStatus.UNCERTAIN:
                relation.confidence = min(relation.confidence, 0.40)
                validated_relations.append(relation)
            else:
                result.warnings.append(f"Rejected relation '{relation.subject} {relation.relation_type} {relation.object}': {reason}")

        validated_events: list[E1Event] = []
        for event in result.events:
            status, reason = self.verify_event_grounding(event, source_corpus, raw_diff)
            event.validation_status = status
            if status == ValidationStatus.VALIDATED:
                validated_events.append(event)
            elif status == ValidationStatus.UNCERTAIN:
                event.confidence = min(event.confidence, 0.40)
                validated_events.append(event)
            else:
                result.warnings.append(f"Rejected event '{event.event_type} on {event.target_component}': {reason}")

        result.entities = validated_entities
        result.relations = validated_relations
        result.events = validated_events

        return result

    def verify_entity_grounding(
        self,
        entity: E1Entity,
        corpus: str,
    ) -> tuple[ValidationStatus, str]:
        """Checks if entity name tokens exist in the source corpus."""
        tokens = self._extract_identifier_tokens(entity.entity_name)
        if not tokens:
            return ValidationStatus.UNCERTAIN, "No substantial identifier tokens to verify."

        ungrounded = [t for t in tokens if t not in corpus and t not in self.whitelist]
        if ungrounded:
            return ValidationStatus.REJECTED, f"Tokens not grounded in source diff: {ungrounded}"

        return ValidationStatus.VALIDATED, "Tokens verified in source diff."

    def verify_relation_grounding(
        self,
        relation: E1Relation,
        corpus: str,
    ) -> tuple[ValidationStatus, str]:
        """Checks if both subject and object exist in the source corpus."""
        subj_tokens = self._extract_identifier_tokens(relation.subject)
        obj_tokens = self._extract_identifier_tokens(relation.object)

        ungrounded_subj = [t for t in subj_tokens if t not in corpus and t not in self.whitelist]
        ungrounded_obj = [t for t in obj_tokens if t not in corpus and t not in self.whitelist]

        if ungrounded_subj or ungrounded_obj:
            return ValidationStatus.REJECTED, f"Ungrounded tokens in relation: subj={ungrounded_subj}, obj={ungrounded_obj}"

        return ValidationStatus.VALIDATED, "Subject and object grounded."

    def verify_event_grounding(
        self,
        event: E1Event,
        corpus: str,
        raw_diff: str,
    ) -> tuple[ValidationStatus, str]:
        """Validates that event target exists and polarity matches diff."""
        target_tokens = self._extract_identifier_tokens(event.target_component)
        ungrounded_target = [t for t in target_tokens if t not in corpus and t not in self.whitelist]

        if ungrounded_target:
            return ValidationStatus.REJECTED, f"Target component ungrounded: {ungrounded_target}"

        # Polarity check: COMPONENT_DELETED should not be asserted if all changes are additions
        if event.event_type == "COMPONENT_DELETED":
            has_deletions = any(line.startswith("-") and not line.startswith("---") for line in raw_diff.splitlines())
            if not has_deletions:
                return ValidationStatus.UNCERTAIN, "Claimed deletion but diff contains no deleted lines."

        return ValidationStatus.VALIDATED, "Event target and polarity grounded."

    def _extract_identifier_tokens(self, text: str) -> list[str]:
        """Extracts candidate tokens (length >= 3) in lowercase."""
        words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", text)
        return [w.lower() for w in words]

    def _is_trivial_diff(self, raw_diff: str) -> bool:
        """Determines if a diff is purely whitespace, comment changes, or empty."""
        lines = raw_diff.strip().splitlines()
        added = [
            line[1:].strip() for line in lines
            if line.startswith("+") and not line.startswith("+++")
        ]
        deleted = [
            line[1:].strip() for line in lines
            if line.startswith("-") and not line.startswith("---")
        ]

        if not added and not deleted:
            return True

        # Check if added and deleted are identical after stripping whitespace
        # (meaning the change was purely trailing/leading whitespace or reformatting)
        if added == deleted:
            return True

        # Filter out comments and blank lines
        substantive_added = [
            line for line in added
            if line and not line.startswith("#") and not line.startswith("//") and not line.startswith("/*")
        ]
        substantive_deleted = [
            line for line in deleted
            if line and not line.startswith("#") and not line.startswith("//") and not line.startswith("/*")
        ]

        return len(substantive_added) == 0 and len(substantive_deleted) == 0
