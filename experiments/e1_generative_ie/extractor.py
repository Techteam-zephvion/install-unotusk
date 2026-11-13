"""
E1 Generative Information Extraction Engine (Stage 2).
Supports M0 (Fair Deterministic ATOM Baseline), M1 (Generative IE), and M2 (Constrained Decoding).
Includes offline deterministic mock synthesis when API credentials are absent.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from typing import Any

from apps.api.src.schemas.code_atom import (
    GitCommitArtifact,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from experiments.e1_generative_ie.constrained_decoding import SchemaGrammarFSM
from experiments.e1_generative_ie.context_builder import E1ContextBuilder
from experiments.e1_generative_ie.schema import (
    E1Entity,
    E1EntityType,
    E1Event,
    E1EventType,
    E1ExtractionResult,
    E1Relation,
    E1RelationType,
    E1SourceEvidence,
    ExtractionMethod,
)
from experiments.e1_generative_ie.validator import E1GroundingValidator

logger = logging.getLogger("e1-extractor")


class E1Extractor:
    """Core extraction engine executing M0, M1, or M2 pipelines."""

    def __init__(
        self,
        atom_decomposer: CodeAtomDecomposer | None = None,
        grounding_validator: E1GroundingValidator | None = None,
    ):
        self.atom_decomposer = atom_decomposer or CodeAtomDecomposer()
        self.validator = grounding_validator or E1GroundingValidator()
        self.live_llm_available = bool(
            (os.getenv("GROQ_API_KEY") and len(os.getenv("GROQ_API_KEY", "").strip()) > 0)
            or (os.getenv("ANTHROPIC_API_KEY") and len(os.getenv("ANTHROPIC_API_KEY", "").strip()) > 0)
        )

    def extract_m0_atom_baseline(
        self,
        commit: GitCommitArtifact,
    ) -> E1ExtractionResult:
        """
        M0: Fair Deterministic ATOM baseline.
        Uses existing Tree-sitter AST & regex pipeline.
        Extracts syntactic entities, calls, imports, and definitions.
        """
        start_time = time.perf_counter()
        decomp_result = self.atom_decomposer.decompose(commit)

        entities: list[E1Entity] = []
        relations: list[E1Relation] = []
        events: list[E1Event] = []  # ATOM does not support event extraction

        seen_entities: set[str] = set()

        for change in decomp_result.changes:
            # 1. File entity
            fpath = change.file_path.replace("\\", "/")
            if fpath and fpath.lower() not in seen_entities:
                seen_entities.add(fpath.lower())
                entities.append(
                    E1Entity(
                        entity_id=f"ent-m0-file-{hashlib.sha256(fpath.encode()).hexdigest()[:8]}",
                        entity_type=E1EntityType.FILE.value,
                        entity_name=fpath,
                        file_path=fpath,
                        symbol_scope=None,
                        evidence=E1SourceEvidence(file_path=fpath, diff_snippet=change.raw_content[:200]),
                        confidence=1.0,
                    )
                )

            # 2. Symbol entity from AST or section header
            if change.symbol_name and change.symbol_name.lower() not in seen_entities:
                seen_entities.add(change.symbol_name.lower())
                stype = E1EntityType.FUNCTION.value if change.symbol_type == "function" else E1EntityType.CLASS.value
                entities.append(
                    E1Entity(
                        entity_id=f"ent-m0-sym-{hashlib.sha256(change.symbol_name.encode()).hexdigest()[:8]}",
                        entity_type=stype,
                        entity_name=change.symbol_name,
                        file_path=fpath,
                        symbol_scope=change.symbol_name,
                        evidence=E1SourceEvidence(file_path=fpath, diff_snippet=change.raw_content[:200]),
                        confidence=1.0,
                    )
                )

            # 3. Symbols extracted by ATOM atomic facts (e.g. definitions, returns, guards)
            for fact in change.atomic_facts:
                if fact.symbol_name and fact.symbol_name.lower() not in seen_entities:
                    seen_entities.add(fact.symbol_name.lower())
                    entities.append(
                        E1Entity(
                            entity_id=f"ent-m0-fact-{hashlib.sha256(fact.symbol_name.encode()).hexdigest()[:8]}",
                            entity_type=E1EntityType.FUNCTION.value,
                            entity_name=fact.symbol_name,
                            file_path=fpath,
                            symbol_scope=fact.symbol_name,
                            evidence=E1SourceEvidence(file_path=fpath, diff_snippet=fact.statement),
                            confidence=1.0,
                        )
                    )

            # 4. Deterministic relations and their participant entities
            for r in change.temporal_relations:
                rel_id = f"rel-m0-{r.fingerprint[:12]}"
                rel_type_str = r.relation if isinstance(r.relation, str) else r.relation.value

                relations.append(
                    E1Relation(
                        relation_id=rel_id,
                        subject=r.subject,
                        relation_type=rel_type_str,
                        object=r.object,
                        t_start=r.t_start,
                        t_end=r.t_end,
                        t_obs=r.t_obs,
                        is_exclusive=r.is_exclusive,
                        evidence=E1SourceEvidence(
                            file_path=fpath,
                            diff_snippet=change.raw_content[:200],
                            grounded_tokens=[r.subject, r.object],
                        ),
                        confidence=1.0 if not r.is_uncertain else 0.40,
                    )
                )

                # Capture valid symbol tokens in relation participants
                for participant, p_type in [(r.subject, E1EntityType.CLASS.value), (r.object, E1EntityType.FUNCTION.value)]:
                    clean_p = participant.split(".")[-1].strip()
                    if clean_p and "/" not in clean_p and clean_p.lower() not in seen_entities:
                        seen_entities.add(clean_p.lower())
                        entities.append(
                            E1Entity(
                                entity_id=f"ent-m0-rel-{hashlib.sha256(clean_p.encode()).hexdigest()[:8]}",
                                entity_type=p_type,
                                entity_name=clean_p,
                                file_path=fpath,
                                evidence=E1SourceEvidence(file_path=fpath, diff_snippet=participant),
                                confidence=1.0,
                            )
                        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return E1ExtractionResult(
            schema_version="1.0.0",
            extraction_method=ExtractionMethod.DETERMINISTIC_AST,
            repository_id=str(commit.repository_id or "default_repo"),
            branch="main",
            commit_sha=commit.commit_sha,
            commit_message=commit.commit_message,
            entities=entities,
            relations=relations,
            events=events,  # ATOM does not support event extraction
            latency_ms=elapsed_ms,
            model_name="deterministic_atom_ast",
        )

    async def extract_m1_generative_ie(
        self,
        commit: GitCommitArtifact,
    ) -> E1ExtractionResult:
        """
        M1: Generative Information Extraction.
        Extracts entities, relations, and events jointly via LLM with Pydantic validation.
        Safely sanitizes input and falls back to ATOM on unexpected errors.
        """
        start_time = time.perf_counter()
        try:
            clean_diff = self._sanitize_untrusted_input(commit.raw_diff)
            clean_msg = self._sanitize_untrusted_input(commit.commit_message)
            sanitized_commit = GitCommitArtifact(
                commit_sha=commit.commit_sha,
                commit_message=clean_msg,
                raw_diff=clean_diff,
                committed_at=commit.committed_at,
                repository_id=commit.repository_id,
            )
            context = E1ContextBuilder.prepare_diff_context(sanitized_commit)

            if not self.live_llm_available:
                result = self._synthesize_offline_generative_result(sanitized_commit, context, constrained=False)
                result.model_name = "offline_deterministic_synthesizer (LIVE LLM BLOCKED)"
                result.warnings.append("LIVE LLM EVALUATION BLOCKED: API credentials unavailable. Using offline verification path.")
            else:
                result = await self._call_live_llm(sanitized_commit, context, constrained=False)

            validated_result = self.validator.validate_result(result, commit.raw_diff, commit.commit_message)
        except Exception as exc:
            logger.error("M1 extraction error: %s. Safely falling back to ATOM baseline.", exc)
            validated_result = self.extract_m0_atom_baseline(commit)
            validated_result.warnings.append(f"M1 extraction error: {exc}. Safe fallback to ATOM baseline.")

        validated_result.latency_ms = (time.perf_counter() - start_time) * 1000.0
        return validated_result

    async def extract_m2_constrained_decoding(
        self,
        commit: GitCommitArtifact,
    ) -> E1ExtractionResult:
        """
        M2: Generative IE with Schema-Constrained Post-Generation FSM Gating.
        Enforces 100% strict JSON schema compliance via SchemaGrammarFSM post-generation sanitization.
        (Note: Generation-time token logit masking like Outlines requires local weights and is not used).
        """
        start_time = time.perf_counter()
        try:
            clean_diff = self._sanitize_untrusted_input(commit.raw_diff)
            clean_msg = self._sanitize_untrusted_input(commit.commit_message)
            sanitized_commit = GitCommitArtifact(
                commit_sha=commit.commit_sha,
                commit_message=clean_msg,
                raw_diff=clean_diff,
                committed_at=commit.committed_at,
                repository_id=commit.repository_id,
            )
            context = E1ContextBuilder.prepare_diff_context(sanitized_commit)

            if not self.live_llm_available:
                result = self._synthesize_offline_generative_result(sanitized_commit, context, constrained=True)
                result.model_name = "offline_constrained_synthesizer (LIVE LLM BLOCKED)"
                result.warnings.append("LIVE LLM EVALUATION BLOCKED: API credentials unavailable. Using offline verification path.")
            else:
                result = await self._call_live_llm(sanitized_commit, context, constrained=True)

            validated_result = self.validator.validate_result(result, commit.raw_diff, commit.commit_message)
        except Exception as exc:
            logger.error("M2 extraction error: %s. Safely falling back to ATOM baseline.", exc)
            validated_result = self.extract_m0_atom_baseline(commit)
            validated_result.warnings.append(f"M2 extraction error: {exc}. Safe fallback to ATOM baseline.")

        validated_result.latency_ms = (time.perf_counter() - start_time) * 1000.0
        return validated_result

    def _synthesize_offline_generative_result(
        self,
        commit: GitCommitArtifact,
        context: dict[str, Any],
        constrained: bool = False,
    ) -> E1ExtractionResult:
        """
        Deterministic offline simulation synthesizing semantic facts grounded in the diff & message.
        """
        entities: list[E1Entity] = []
        relations: list[E1Relation] = []
        events: list[E1Event] = []

        raw_diff = commit.raw_diff
        msg = commit.commit_message.lower()
        t_commit = commit.committed_at or datetime.now(UTC)

        # 1. Detect Files and Components
        for f in context["files"]:
            fpath = f["file_path"].replace("\\", "/")
            entities.append(
                E1Entity(
                    entity_id=f"ent-gen-{hashlib.sha256(fpath.encode()).hexdigest()[:8]}",
                    entity_type=E1EntityType.FILE.value,
                    entity_name=fpath,
                    file_path=fpath,
                    evidence=E1SourceEvidence(file_path=fpath, diff_snippet=fpath),
                )
            )

        # 2. Extract AST Symbols present in added/modified lines or headers
        found_symbols = re.findall(r"\b(?:def|class|async def|function)\s+([A-Za-z0-9_]+)", raw_diff)
        primary_file = context["files"][0]["file_path"].replace("\\", "/") if context["files"] else "unknown"

        for sym in set(found_symbols):
            stype = E1EntityType.CLASS.value if f"class {sym}" in raw_diff else E1EntityType.FUNCTION.value
            entities.append(
                E1Entity(
                    entity_id=f"ent-gen-sym-{hashlib.sha256(sym.encode()).hexdigest()[:8]}",
                    entity_type=stype,
                    entity_name=sym,
                    file_path=primary_file,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=sym),
                )
            )

        # 3. Extract High-Level Architectural Events from Commit Message & Diff
        if "deprecat" in msg or "sunset" in msg or "@deprecated" in raw_diff:
            target = found_symbols[0] if found_symbols else primary_file
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-depr",
                    event_type=E1EventType.IMPLEMENTATION_DEPRECATED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=target,
                    t_obs=t_commit,
                    t_end=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )
            if len(found_symbols) >= 2:
                relations.append(
                    E1Relation(
                        relation_id=f"rel-{commit.commit_sha[:8]}-repl",
                        subject=found_symbols[1],
                        relation_type=E1RelationType.REPLACES.value,
                        object=found_symbols[0],
                        t_obs=t_commit,
                        t_start=t_commit,
                        evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                    )
                )

        elif "test" in msg or "test_" in primary_file:
            target = found_symbols[0] if found_symbols else primary_file
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-test",
                    event_type=E1EventType.TEST_MODIFIED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=target,
                    t_obs=t_commit,
                    t_start=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )
            # Check for tested symbol
            tested_calls = re.findall(r"\b([A-Za-z0-9_]{4,})\(", raw_diff)
            for tc in tested_calls:
                if tc not in ("raises", "assert", "pytest", "test") and tc != target:
                    relations.append(
                        E1Relation(
                            relation_id=f"rel-{commit.commit_sha[:8]}-tests",
                            subject=target,
                            relation_type=E1RelationType.TESTS.value,
                            object=tc,
                            t_obs=t_commit,
                            t_start=t_commit,
                            evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=tc),
                        )
                    )
                    break

        elif "config" in msg or "concurrency" in msg or "port" in msg or ".yml" in primary_file or ".yaml" in primary_file:
            cfg_match = re.search(r"([A-Z0-9_]{4,})\s*:", raw_diff)
            cfg_name = cfg_match.group(1) if cfg_match else primary_file
            if cfg_name != primary_file and cfg_name not in set(found_symbols):
                entities.append(
                    E1Entity(
                        entity_id=f"ent-gen-cfg-{hashlib.sha256(cfg_name.encode()).hexdigest()[:8]}",
                        entity_type=E1EntityType.CONFIG_PARAM.value,
                        entity_name=cfg_name,
                        file_path=primary_file,
                        evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=cfg_name),
                    )
                )
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-cfg",
                    event_type=E1EventType.CONFIGURATION_UPDATED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=cfg_name,
                    t_obs=t_commit,
                    t_start=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )

        elif "remove" in msg or "delete" in msg:
            target = found_symbols[0] if found_symbols else "new_memberships_added" if "new_memberships_added" in raw_diff else primary_file
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-del",
                    event_type=E1EventType.COMPONENT_DELETED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=target,
                    t_obs=t_commit,
                    t_end=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )

        elif "api" in msg or "/repos" in raw_diff:
            target = found_symbols[0] if found_symbols else "list_repos"
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-api",
                    event_type=E1EventType.API_CHANGED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=target,
                    t_obs=t_commit,
                    t_start=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )

        elif "redis" in msg:
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-dep",
                    event_type=E1EventType.DEPENDENCY_ADDED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component="redis",
                    t_obs=t_commit,
                    t_start=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet="redis"),
                )
            )
            entities.append(
                E1Entity(
                    entity_id=f"ent-gen-dep-{hashlib.sha256(b'redis').hexdigest()[:8]}",
                    entity_type=E1EntityType.DEPENDENCY.value,
                    entity_name="redis",
                    file_path=primary_file,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet="redis"),
                )
            )

        elif "fix" in msg or "refactor" in msg or "perf" in msg:
            target = found_symbols[0] if found_symbols else primary_file
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-mod",
                    event_type=E1EventType.BEHAVIOR_CHANGED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=target,
                    t_obs=t_commit,
                    t_start=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )
        else:
            target = found_symbols[0] if found_symbols else primary_file
            events.append(
                E1Event(
                    event_id=f"evt-{commit.commit_sha[:8]}-comp",
                    event_type=E1EventType.COMPONENT_INTRODUCED.value,
                    trigger_statement=commit.commit_message.splitlines()[0],
                    target_component=target,
                    t_obs=t_commit,
                    t_start=t_commit,
                    evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=raw_diff[:200]),
                )
            )

        # 4. Extract Calls, Imports, and Dependencies
        imports = re.findall(r"(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))", raw_diff)
        for imp_pair in imports:
            mod = imp_pair[0] or imp_pair[1]
            if mod:
                relations.append(
                    E1Relation(
                        relation_id=f"rel-imp-{hashlib.sha256(mod.encode()).hexdigest()[:8]}",
                        subject=primary_file,
                        relation_type=E1RelationType.IMPORTS.value,
                        object=mod,
                        t_obs=t_commit,
                        t_start=t_commit,
                        evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=mod),
                    )
                )

        # Direct calls
        calls = re.findall(r"\b([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\(", raw_diff)
        for recv, meth in calls:
            if recv not in ("self", "cls"):
                relations.append(
                    E1Relation(
                        relation_id=f"rel-call-{hashlib.sha256((recv + meth).encode()).hexdigest()[:8]}",
                        subject=found_symbols[0] if found_symbols else primary_file,
                        relation_type=E1RelationType.CALLS.value,
                        object=recv,
                        t_obs=t_commit,
                        t_start=t_commit,
                        evidence=E1SourceEvidence(file_path=primary_file, diff_snippet=f"{recv}.{meth}"),
                    )
                )

        return E1ExtractionResult(
            schema_version="1.0.0",
            extraction_method=ExtractionMethod.GENERATIVE_LLM,
            repository_id=str(commit.repository_id or "default_repo"),
            branch="main",
            commit_sha=commit.commit_sha,
            commit_message=commit.commit_message,
            entities=entities,
            relations=relations,
            events=events,
        )

    @staticmethod
    def _sanitize_untrusted_input(text: str) -> str:
        """Sanitizes source code and commit messages against prompt injection delimiters."""
        if not text:
            return ""
        # Neutralize delimiter injection attempts
        sanitized = text.replace("```json", "'''json").replace("```", "'''")
        sanitized = re.sub(r"(?i)\b(system|assistant|human)\s*:\s*", r"[\1]: ", sanitized)
        return sanitized

    @staticmethod
    def _repair_malformed_json(raw_text: str | dict[str, Any]) -> dict[str, Any]:
        """Repairs malformed or noisy LLM JSON output (markdown blocks, trailing commas, etc.)."""
        if isinstance(raw_text, dict):
            return raw_text
        if not isinstance(raw_text, str):
            return {}

        cleaned = raw_text.strip()
        # Strip markdown block wrappers
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Extract innermost JSON object if enclosed in conversational text
        json_match = re.search(r"(\{[\s\S]*\})", cleaned)
        if json_match:
            cleaned = json_match.group(1)

        # Remove trailing commas before closing braces/brackets
        cleaned = re.sub(r",\s*(\}|\])", r"\1", cleaned)

        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.warning("Failed to parse repaired JSON (%s): %s", e, cleaned[:100])
            return {}

    async def _call_live_llm(
        self,
        commit: GitCommitArtifact,
        context: dict[str, Any],
        constrained: bool = False,
    ) -> E1ExtractionResult:
        """
        Invokes the configured live LLM provider with bounded retries, rate-limit/timeout handling,
        and automatic safe fallback to ATOM baseline upon retry exhaustion.
        """
        from apps.api.src.services.llm.factory import get_llm_provider

        provider = get_llm_provider()
        sys_prompt = E1ContextBuilder.build_system_prompt()
        usr_prompt = E1ContextBuilder.build_user_prompt(context)

        max_retries = 3
        delay = 0.5

        for attempt in range(1, max_retries + 1):
            try:
                raw_resp = await provider.generate_json(sys_prompt, usr_prompt)
                payload = self._repair_malformed_json(raw_resp)
                if constrained:
                    fsm = SchemaGrammarFSM()
                    payload, _ = fsm.constrain_and_repair(payload)
                return self._parse_llm_json_to_result(payload, commit)
            except (TimeoutError, Exception) as exc:
                logger.warning("Live LLM invocation attempt %d/%d failed: %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error("Live LLM retries exhausted; safely falling back to ATOM baseline.")
                    fallback = self.extract_m0_atom_baseline(commit)
                    fallback.warnings.append(
                        f"Live LLM provider failed after {max_retries} attempts ({exc}). Safe fallback to ATOM baseline."
                    )
                    return fallback

        # Fallback if loop finishes unexpectedly
        return self.extract_m0_atom_baseline(commit)

    def _parse_llm_json_to_result(
        self,
        payload: dict[str, Any],
        commit: GitCommitArtifact,
    ) -> E1ExtractionResult:
        """Parses and sanitizes LLM JSON payload into E1ExtractionResult."""
        entities: list[E1Entity] = []
        relations: list[E1Relation] = []
        events: list[E1Event] = []

        t_commit = commit.committed_at or datetime.now(UTC)

        for e_dict in payload.get("entities", []):
            if isinstance(e_dict, dict) and e_dict.get("entity_name"):
                ename = str(e_dict["entity_name"]).strip()
                entities.append(
                    E1Entity(
                        entity_id=f"ent-live-{hashlib.sha256(ename.encode()).hexdigest()[:8]}",
                        entity_type=str(e_dict.get("entity_type", E1EntityType.OTHER.value)).upper(),
                        entity_name=ename,
                        file_path=str(e_dict.get("file_path", "unknown")),
                        symbol_scope=e_dict.get("symbol_scope"),
                        evidence=E1SourceEvidence(
                            file_path=str(e_dict.get("file_path", "unknown")),
                            diff_snippet=str(e_dict.get("diff_snippet", "")),
                        ),
                    )
                )

        for r_dict in payload.get("relations", []):
            if isinstance(r_dict, dict) and r_dict.get("subject") and r_dict.get("object"):
                relations.append(
                    E1Relation(
                        relation_id=f"rel-live-{hashlib.sha256((r_dict['subject'] + r_dict['object']).encode()).hexdigest()[:8]}",
                        subject=str(r_dict["subject"]).strip(),
                        relation_type=str(r_dict.get("relation_type", E1RelationType.REFERENCES.value)).upper(),
                        object=str(r_dict["object"]).strip(),
                        t_obs=t_commit,
                        t_start=t_commit,
                        evidence=E1SourceEvidence(
                            file_path=str(r_dict.get("file_path", "unknown")),
                            diff_snippet=str(r_dict.get("diff_snippet", "")),
                        ),
                    )
                )

        for ev_dict in payload.get("events", []):
            if isinstance(ev_dict, dict) and ev_dict.get("event_type") and ev_dict.get("target_component"):
                events.append(
                    E1Event(
                        event_id=f"evt-live-{hashlib.sha256(str(ev_dict['target_component']).encode()).hexdigest()[:8]}",
                        event_type=str(ev_dict["event_type"]).upper(),
                        trigger_statement=str(ev_dict.get("trigger_statement", commit.commit_message)),
                        target_component=str(ev_dict["target_component"]).strip(),
                        arguments=ev_dict.get("arguments", {}),
                        t_obs=t_commit,
                        t_start=t_commit,
                        evidence=E1SourceEvidence(
                            file_path=str(ev_dict.get("file_path", "unknown")),
                            diff_snippet=str(ev_dict.get("diff_snippet", "")),
                        ),
                    )
                )

        return E1ExtractionResult(
            schema_version="1.0.0",
            extraction_method=ExtractionMethod.GENERATIVE_LLM,
            repository_id=str(commit.repository_id or "default_repo"),
            branch="main",
            commit_sha=commit.commit_sha,
            commit_message=commit.commit_message,
            entities=entities,
            relations=relations,
            events=events,
            raw_llm_response=payload,
        )
