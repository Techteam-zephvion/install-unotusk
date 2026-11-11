"""
E1 Human Review & Ground-Truth Annotation Tool.
Provides a functional, lightweight review workflow for the 40 E1 benchmark scenarios.
Supports inspecting, approving, rejecting, editing, and adding entities, relations,
and events, with audit provenance and persistence.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.e1_generative_ie.data.dataset import (
    E1TestCase,
    load_e1_dataset,
)

logger = logging.getLogger("e1-review-tool")

DEFAULT_ANNOTATION_FILE = Path(__file__).parent / "data" / "e1_human_review_annotations.json"


class E1ReviewSession:
    """Manages the interactive and programmatic review workflow for E1 benchmark annotations."""

    def __init__(self, annotation_file: Path | str | None = None):
        self.annotation_file = Path(annotation_file or DEFAULT_ANNOTATION_FILE)
        self.cases: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Loads scenarios from the annotation JSON file or initial dataset."""
        if self.annotation_file.exists():
            with open(self.annotation_file, encoding="utf-8") as f:
                self.cases = json.load(f)
        else:
            # Bootstrap from dataset.py
            raw_cases: list[E1TestCase] = load_e1_dataset()
            self.cases = []
            for c in raw_cases:
                case_dict = {
                    "case_id": c.case_id,
                    "split": c.split,
                    "category": c.category,
                    "language": c.language,
                    "commit_sha": c.commit.commit_sha,
                    "commit_message": c.commit.commit_message,
                    "author_timestamp": c.commit.author_date.isoformat() if c.commit.author_date else None,
                    "raw_diff": c.commit.raw_diff,
                    "annotation_status": "PROVISIONAL_AI_DRAFT",
                    "review_metadata": {
                        "reviewed_by": None,
                        "review_date": None,
                        "review_status": "PENDING_INDEPENDENT_HUMAN_REVIEW",
                        "reviewer_notes": "",
                    },
                    "expected_entities": [asdict(e) for e in c.expected_entities],
                    "expected_relations": [asdict(r) for r in c.expected_relations],
                    "expected_events": [asdict(ev) for ev in c.expected_events],
                    "is_ambiguous": c.is_ambiguous,
                    "is_trivial": c.is_trivial,
                }
                self.cases.append(case_dict)

    def save(self, target_path: Path | str | None = None) -> None:
        """Saves current review state to disk."""
        dest = Path(target_path or self.annotation_file)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(self.cases, f, indent=2)
        logger.info("Saved review session with %d scenarios to %s", len(self.cases), dest)

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        """Retrieves a specific case by case_id."""
        for c in self.cases:
            if c["case_id"] == case_id:
                return c
        return None

    def list_cases(
        self,
        split: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lists cases filtered by split, status, or category."""
        results = []
        for c in self.cases:
            if split and c.get("split") != split:
                continue
            if status and c.get("annotation_status") != status:
                continue
            if category and c.get("category") != category:
                continue
            results.append(c)
        return results

    def format_case_display(self, case_id: str) -> str:
        """Formats the case details, diff, commit message, and annotations for review display."""
        c = self.get_case(case_id)
        if not c:
            return f"Error: Case '{case_id}' not found."

        meta = c.get("review_metadata", {})
        lines = [
            "=" * 70,
            f"Case ID:        {c['case_id']}  [{c.get('split', 'unknown').upper()}]",
            f"Category:       {c.get('category')} ({c.get('language')})",
            f"Commit SHA:     {c.get('commit_sha')}",
            f"Status:         {c.get('annotation_status')}",
            f"Reviewer:       {meta.get('reviewed_by') or 'None'}",
            f"Review Date:    {meta.get('review_date') or 'Pending'}",
            f"Review Notes:   {meta.get('reviewer_notes') or 'None'}",
            "-" * 70,
            "COMMIT MESSAGE:",
            c.get("commit_message", "").strip(),
            "-" * 70,
            "RAW DIFF:",
            c.get("raw_diff", "").strip(),
            "-" * 70,
            f"ENTITIES ({len(c.get('expected_entities', []))}):",
        ]
        for i, ent in enumerate(c.get("expected_entities", [])):
            atom_tag = "[ATOM]" if ent.get("is_supported_by_atom") else "[SEMANTIC]"
            lines.append(
                f"  [{i}] {ent.get('name')} ({ent.get('type')}) {atom_tag} | span: '{ent.get('evidence_span')}'"
            )

        lines.append(f"\nRELATIONS ({len(c.get('expected_relations', []))}):")
        for i, rel in enumerate(c.get("expected_relations", [])):
            atom_tag = "[ATOM]" if rel.get("is_supported_by_atom") else "[SEMANTIC]"
            lines.append(
                f"  [{i}] ({rel.get('subject')}) --[{rel.get('rel')}]--> ({rel.get('obj')}) {atom_tag}"
            )

        lines.append(f"\nEVENTS ({len(c.get('expected_events', []))}):")
        for i, ev in enumerate(c.get("expected_events", [])):
            lines.append(
                f"  [{i}] {ev.get('type')} on '{ev.get('target')}' | trigger: '{ev.get('trigger_statement')}'"
            )
        lines.append("=" * 70)
        return "\n".join(lines)

    def approve_case(self, case_id: str, reviewer: str, notes: str = "") -> bool:
        """Approves the annotations for a scenario as HUMAN_VERIFIED."""
        if not reviewer or not reviewer.strip():
            logger.warning("Approval rejected: reviewer identifier required to prevent false certification.")
            return False
        c = self.get_case(case_id)
        if not c:
            return False
        c["annotation_status"] = "HUMAN_VERIFIED"
        c["review_metadata"] = {
            "reviewed_by": reviewer.strip(),
            "review_date": datetime.now(UTC).isoformat(),
            "review_status": "APPROVED",
            "reviewer_notes": notes,
        }
        return True

    def reject_case(self, case_id: str, reviewer: str, reason: str) -> bool:
        """Rejects draft annotations for a scenario and flags for revision."""
        if not reviewer or not reviewer.strip():
            logger.warning("Rejection rejected: reviewer identifier required.")
            return False
        c = self.get_case(case_id)
        if not c:
            return False
        c["annotation_status"] = "REJECTED"
        c["review_metadata"] = {
            "reviewed_by": reviewer.strip(),
            "review_date": datetime.now(UTC).isoformat(),
            "review_status": "REJECTED",
            "reviewer_notes": reason,
        }
        return True

    def mark_uncertain(self, case_id: str, reviewer: str, notes: str = "") -> bool:
        """Marks scenario as ambiguous or needing clarification."""
        if not reviewer or not reviewer.strip():
            return False
        c = self.get_case(case_id)
        if not c:
            return False
        c["annotation_status"] = "NEEDS_REVIEW"
        c["is_ambiguous"] = True
        c["review_metadata"] = {
            "reviewed_by": reviewer.strip(),
            "review_date": datetime.now(UTC).isoformat(),
            "review_status": "MARKED_UNCERTAIN",
            "reviewer_notes": notes,
        }
        return True

    def add_entity(
        self,
        case_id: str,
        name: str,
        entity_type: str,
        evidence_span: str = "",
        is_supported_by_atom: bool = True,
    ) -> bool:
        """Adds a missing expected entity to the scenario."""
        c = self.get_case(case_id)
        if not c:
            return False
        new_ent = {
            "name": name,
            "type": entity_type.upper(),
            "evidence_span": evidence_span or name,
            "is_supported_by_atom": is_supported_by_atom,
        }
        c.setdefault("expected_entities", []).append(new_ent)
        return True

    def edit_entity(
        self,
        case_id: str,
        entity_idx: int,
        name: str | None = None,
        entity_type: str | None = None,
        evidence_span: str | None = None,
        is_supported_by_atom: bool | None = None,
    ) -> bool:
        """Edits an existing entity annotation."""
        c = self.get_case(case_id)
        if not c or entity_idx < 0 or entity_idx >= len(c.get("expected_entities", [])):
            return False
        ent = c["expected_entities"][entity_idx]
        if name is not None:
            ent["name"] = name
        if entity_type is not None:
            ent["type"] = entity_type.upper()
        if evidence_span is not None:
            ent["evidence_span"] = evidence_span
        if is_supported_by_atom is not None:
            ent["is_supported_by_atom"] = is_supported_by_atom
        return True

    def delete_entity(self, case_id: str, entity_idx: int) -> bool:
        """Deletes an entity annotation by index."""
        c = self.get_case(case_id)
        if not c or entity_idx < 0 or entity_idx >= len(c.get("expected_entities", [])):
            return False
        c["expected_entities"].pop(entity_idx)
        return True

    def add_relation(
        self,
        case_id: str,
        subject: str,
        rel: str,
        obj: str,
        is_supported_by_atom: bool = True,
    ) -> bool:
        """Adds a missing relation annotation."""
        c = self.get_case(case_id)
        if not c:
            return False
        new_rel = {
            "subject": subject,
            "rel": rel.upper(),
            "obj": obj,
            "is_supported_by_atom": is_supported_by_atom,
        }
        c.setdefault("expected_relations", []).append(new_rel)
        return True

    def edit_relation(
        self,
        case_id: str,
        relation_idx: int,
        subject: str | None = None,
        rel: str | None = None,
        obj: str | None = None,
        is_supported_by_atom: bool | None = None,
    ) -> bool:
        """Edits an existing relation annotation."""
        c = self.get_case(case_id)
        if not c or relation_idx < 0 or relation_idx >= len(c.get("expected_relations", [])):
            return False
        r = c["expected_relations"][relation_idx]
        if subject is not None:
            r["subject"] = subject
        if rel is not None:
            r["rel"] = rel.upper()
        if obj is not None:
            r["obj"] = obj
        if is_supported_by_atom is not None:
            r["is_supported_by_atom"] = is_supported_by_atom
        return True

    def delete_relation(self, case_id: str, relation_idx: int) -> bool:
        """Deletes a relation annotation by index."""
        c = self.get_case(case_id)
        if not c or relation_idx < 0 or relation_idx >= len(c.get("expected_relations", [])):
            return False
        c["expected_relations"].pop(relation_idx)
        return True

    def add_event(
        self,
        case_id: str,
        event_type: str,
        target: str,
        trigger_statement: str,
        temporal_attribute: str = "t_obs",
        evidence_span: str = "",
        is_supported_by_atom: bool = False,
    ) -> bool:
        """Adds a missing event annotation."""
        c = self.get_case(case_id)
        if not c:
            return False
        new_ev = {
            "type": event_type.upper(),
            "target": target,
            "trigger_statement": trigger_statement,
            "temporal_attribute": temporal_attribute,
            "arguments": {},
            "evidence_span": evidence_span or target,
            "is_supported_by_atom": is_supported_by_atom,
        }
        c.setdefault("expected_events", []).append(new_ev)
        return True

    def edit_event(
        self,
        case_id: str,
        event_idx: int,
        event_type: str | None = None,
        target: str | None = None,
        trigger_statement: str | None = None,
        temporal_attribute: str | None = None,
        is_supported_by_atom: bool | None = None,
    ) -> bool:
        """Edits an existing event annotation."""
        c = self.get_case(case_id)
        if not c or event_idx < 0 or event_idx >= len(c.get("expected_events", [])):
            return False
        ev = c["expected_events"][event_idx]
        if event_type is not None:
            ev["type"] = event_type.upper()
        if target is not None:
            ev["target"] = target
        if trigger_statement is not None:
            ev["trigger_statement"] = trigger_statement
        if temporal_attribute is not None:
            ev["temporal_attribute"] = temporal_attribute
        if is_supported_by_atom is not None:
            ev["is_supported_by_atom"] = is_supported_by_atom
        return True

    def delete_event(self, case_id: str, event_idx: int) -> bool:
        """Deletes an event annotation by index."""
        c = self.get_case(case_id)
        if not c or event_idx < 0 or event_idx >= len(c.get("expected_events", [])):
            return False
        c["expected_events"].pop(event_idx)
        return True

    def get_progress_summary(self) -> dict[str, Any]:
        """Calculates review progress, distribution across splits, and verification counts."""
        total = len(self.cases)
        status_counts: dict[str, int] = {}
        split_counts: dict[str, int] = {}
        reviewed_count = 0

        for c in self.cases:
            st = c.get("annotation_status", "PROVISIONAL_AI_DRAFT")
            sp = c.get("split", "unknown")
            status_counts[st] = status_counts.get(st, 0) + 1
            split_counts[sp] = split_counts.get(sp, 0) + 1
            if st in ("HUMAN_VERIFIED", "REJECTED"):
                reviewed_count += 1

        return {
            "total_cases": total,
            "reviewed_cases": reviewed_count,
            "pending_review": total - reviewed_count,
            "completion_rate_pct": round((reviewed_count / total * 100.0) if total else 0.0, 1),
            "status_breakdown": status_counts,
            "split_breakdown": split_counts,
        }

    def export_reviewed_dataset(self, export_path: Path | str) -> None:
        """Exports verified/annotated dataset for downstream benchmarks."""
        dest = Path(export_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(self.cases, f, indent=2)


def main() -> None:
    """CLI interface for the annotation review utility."""
    parser = argparse.ArgumentParser(description="E1 Annotation Human Review Tool")
    parser.add_argument("--list", action="store_true", help="List all benchmark cases and statuses")
    parser.add_argument("--summary", action="store_true", help="Show review progress summary")
    parser.add_argument("--show", type=str, help="Display details of a specific case_id")
    parser.add_argument("--approve", type=str, help="Approve case_id as HUMAN_VERIFIED")
    parser.add_argument("--reject", type=str, help="Reject case_id annotations")
    parser.add_argument("--uncertain", type=str, help="Mark case_id as uncertain / NEEDS_REVIEW")
    parser.add_argument("--reviewer", type=str, default="", help="Reviewer identifier (required for approval/rejection)")
    parser.add_argument("--notes", type=str, default="", help="Review notes or rejection reason")
    parser.add_argument("--export", type=str, help="Export reviewed cases to JSON file path")

    args = parser.parse_args()
    session = E1ReviewSession()

    if args.summary:
        summary = session.get_progress_summary()
        print("\n=== E1 ANNOTATION REVIEW SUMMARY ===")
        print(f"Total Scenarios:    {summary['total_cases']}")
        print(f"Reviewed Scenarios: {summary['reviewed_cases']} ({summary['completion_rate_pct']}%)")
        print(f"Pending Review:     {summary['pending_review']}")
        print(f"Status Counts:      {summary['status_breakdown']}")
        print(f"Splits:             {summary['split_breakdown']}\n")

    elif args.list:
        cases = session.list_cases()
        print(f"\nFound {len(cases)} benchmark cases:")
        for c in cases:
            meta = c.get("review_metadata", {})
            print(
                f"  [{c['case_id']}] {c.get('split', '').upper():4} | {c.get('category'):14} | {c.get('annotation_status'):22} | reviewer: {meta.get('reviewed_by') or '-'}"
            )
        print()

    elif args.show:
        print(session.format_case_display(args.show))

    elif args.approve:
        if not args.reviewer:
            print("Error: --reviewer <name> is mandatory to approve an annotation.")
            return
        success = session.approve_case(args.approve, args.reviewer, args.notes)
        if success:
            session.save()
            print(f"Case '{args.approve}' approved by {args.reviewer}.")
        else:
            print(f"Error: Case '{args.approve}' not found or approval invalid.")

    elif args.reject:
        if not args.reviewer:
            print("Error: --reviewer <name> is mandatory to reject an annotation.")
            return
        success = session.reject_case(args.reject, args.reviewer, args.notes)
        if success:
            session.save()
            print(f"Case '{args.reject}' rejected by {args.reviewer}.")
        else:
            print(f"Error: Case '{args.reject}' not found.")

    elif args.uncertain:
        if not args.reviewer:
            print("Error: --reviewer <name> is mandatory to mark uncertainty.")
            return
        success = session.mark_uncertain(args.uncertain, args.reviewer, args.notes)
        if success:
            session.save()
            print(f"Case '{args.uncertain}' marked uncertain by {args.reviewer}.")
        else:
            print(f"Error: Case '{args.uncertain}' not found.")

    elif args.export:
        session.export_reviewed_dataset(args.export)
        print(f"Exported dataset to {args.export}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
