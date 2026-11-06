"""
Context preparation engine for E1 Generative Information Extraction.
Prepares code-change context from Git diffs, commit messages, and AST symbol catalogs.
"""

from typing import Any

from apps.api.src.schemas.code_atom import GitCommitArtifact
from apps.api.src.services.code_atom.diff_parser import parse_unified_diff


class E1ContextBuilder:
    """Constructs structured extraction prompts and contexts for LLM ingestion."""

    @staticmethod
    def prepare_diff_context(
        commit: GitCommitArtifact,
        max_diff_lines: int = 500,
    ) -> dict[str, Any]:
        """
        Parses diff artifacts and compiles concise summary metadata.
        """
        file_diffs = list(commit.file_diffs)
        if not file_diffs and commit.raw_diff:
            file_diffs = parse_unified_diff(commit.raw_diff)

        file_summaries = []
        for fd in file_diffs:
            added_lines_count = sum(len(h.added_lines) for h in fd.hunks)
            deleted_lines_count = sum(len(h.deleted_lines) for h in fd.hunks)
            hunk_headers = [h.header for h in fd.hunks if h.header]

            file_summaries.append({
                "file_path": fd.new_path,
                "old_path": fd.old_path,
                "change_type": fd.change_type.value,
                "hunk_count": len(fd.hunks),
                "added_lines_count": added_lines_count,
                "deleted_lines_count": deleted_lines_count,
                "hunk_headers": hunk_headers,
            })

        # Truncate raw diff safely if overly long to prevent context overflow
        diff_lines = commit.raw_diff.splitlines()
        truncated = False
        if len(diff_lines) > max_diff_lines:
            truncated = True
            diff_text = "\n".join(diff_lines[:max_diff_lines]) + "\n... [DIFF TRUNCATED]"
        else:
            diff_text = commit.raw_diff

        return {
            "commit_sha": commit.commit_sha,
            "commit_message": commit.commit_message.strip(),
            "author_name": commit.author_name or "Unknown",
            "committed_at": commit.committed_at.isoformat() if commit.committed_at else None,
            "files": file_summaries,
            "raw_diff": diff_text,
            "is_truncated": truncated,
        }

    @staticmethod
    def build_system_prompt() -> str:
        """Constructs the schema-conditioned instruction prompt for Generative IE."""
        return (
            "You are an authoritative Code Lane Generative Information Extraction Engine (E1).\n"
            "Your objective is to transform code diffs and paired commit messages into verified, structured information:\n"
            "1. Entities: Software components (SERVICE, MODULE, FILE, CLASS, FUNCTION, API, DEPENDENCY, CONFIG_PARAM, TEST, DATASTORE).\n"
            "2. Relations: Directed connections (CALLS, IMPORTS, DEFINES, INHERITS, MUTATES, CONFIGURES, VALIDATES, RAISES, REFERENCES, DEPENDS_ON, REPLACES, SUPERSEDES, TESTS).\n"
            "3. Events: Discrete evolution occurrences (COMPONENT_INTRODUCED, COMPONENT_MODIFIED, COMPONENT_DELETED, DEPENDENCY_ADDED, DEPENDENCY_REMOVED, API_CHANGED, BEHAVIOR_CHANGED, TEST_MODIFIED, CONFIGURATION_UPDATED, IMPLEMENTATION_DEPRECATED).\n\n"
            "CRITICAL EXTRACTION & GROUNDING RULES:\n"
            "- Grounding: Every entity, relation object, and event MUST be grounded in exact tokens present in the diff, symbol scope, or commit message.\n"
            "- Zero Hallucination: Do NOT invent unmentioned third-party packages, external APIs, or business logic.\n"
            "- Deletions: Deleted lines (marked with '-') represent ceased capabilities. Do NOT treat removed code as active functionality. Assign COMPONENT_DELETED or REMOVAL.\n"
            "- Intent & Rationale: Use the commit message to identify the causal reason behind the code change.\n"
            "- Abstention: If the diff contains only trivial whitespace, comment edits, or ambiguous scalar assignments without semantic context, return empty lists.\n\n"
            "Respond strictly in valid JSON matching this schema:\n"
            "{\n"
            '  "entities": [\n'
            '    {"entity_name": "string", "entity_type": "SERVICE|MODULE|FILE|CLASS|FUNCTION|API|DEPENDENCY|CONFIG_PARAM|TEST|DATASTORE", "file_path": "string", "symbol_scope": "string|null", "diff_snippet": "string"}\n'
            "  ],\n"
            '  "relations": [\n'
            '    {"subject": "string", "relation_type": "CALLS|IMPORTS|DEFINES|INHERITS|MUTATES|CONFIGURES|VALIDATES|RAISES|REFERENCES|DEPENDS_ON|REPLACES|SUPERSEDES|TESTS", "object": "string", "file_path": "string", "diff_snippet": "string"}\n'
            "  ],\n"
            '  "events": [\n'
            '    {"event_type": "COMPONENT_INTRODUCED|COMPONENT_MODIFIED|COMPONENT_DELETED|DEPENDENCY_ADDED|DEPENDENCY_REMOVED|API_CHANGED|BEHAVIOR_CHANGED|TEST_MODIFIED|CONFIGURATION_UPDATED|IMPLEMENTATION_DEPRECATED", "trigger_statement": "string", "target_component": "string", "arguments": {}, "file_path": "string", "diff_snippet": "string"}\n'
            "  ]\n"
            "}"
        )

    @staticmethod
    def build_user_prompt(context: dict[str, Any]) -> str:
        """Constructs the per-commit extraction query."""
        files_str = "\n".join(
            f"- {f['file_path']} ({f['change_type']}, +{f['added_lines_count']}/-{f['deleted_lines_count']} lines)"
            for f in context["files"]
        )

        return (
            f"Commit SHA: {context['commit_sha']}\n"
            f"Commit Message: {context['commit_message']}\n"
            f"Author Date: {context['committed_at'] or 'Unknown'}\n"
            f"Files Affected:\n{files_str}\n\n"
            f"Raw Unified Diff:\n```diff\n{context['raw_diff']}\n```\n\n"
            "Extract all grounded entities, relationships, and software evolution events from this commit."
        )
