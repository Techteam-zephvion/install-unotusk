import logging
import os
import posixpath
from collections import defaultdict
from typing import Any

from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
)
from apps.api.src.services.discovery_engine.base import (
    CandidateFinding,
    DiscoveryAnalyzer,
    DiscoveryContext,
)

logger = logging.getLogger("unotusk-discovery")


class CircularDependencyAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.CIRCULAR_DEPENDENCY

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        # 1. Build directed graph: file_path -> list of (target_file_path, dependency_obj)
        graph: dict[str, list[tuple[str, Any]]] = defaultdict(list)
        all_paths = set(ctx.file_by_path.keys())

        for src_file in ctx.files:
            deps = ctx.dependencies_by_file_id.get(src_file.id, [])
            for dep in deps:
                resolved_target = self._resolve_target_path(
                    src_path=src_file.path,
                    target=ctx.get_target_for_dep(dep),
                    all_paths=all_paths,
                )
                if resolved_target and resolved_target != src_file.path:
                    graph[src_file.path].append((resolved_target, dep))

        # 2. Find cycles using DFS
        cycles = self._find_cycles(graph)

        for cycle in cycles:
            # cycle is a list of file paths e.g. [A, B, C, A]
            affected_files = list(dict.fromkeys(cycle[:-1]))
            cycle_str = " -> ".join(affected_files) + f" -> {affected_files[0]}"

            evidence_items: list[dict[str, Any]] = []
            for i in range(len(affected_files)):
                src = affected_files[i]
                dst = affected_files[(i + 1) % len(affected_files)]
                # Find matching dependency edge
                edge_dep = next((d for target, d in graph.get(src, []) if target == dst), None)
                evidence_items.append({
                    "type": "dependency_edge",
                    "file": src,
                    "target": dst,
                    "lines": f"{edge_dep.line_number}" if edge_dep and edge_dep.line_number else "N/A",
                    "snippet": f"{src} imports {dst}",
                })

            severity = FindingSeverity.HIGH if len(affected_files) >= 3 else FindingSeverity.MEDIUM

            findings.append(
                CandidateFinding(
                    category=FindingCategory.CIRCULAR_DEPENDENCY,
                    title=f"Circular dependency: {cycle_str}",
                    description=(
                        f"A circular dependency loop was detected between {len(affected_files)} components: "
                        f"{cycle_str}."
                    ),
                    why_it_matters=(
                        "Circular dependencies can cause initialization order bugs, memory leaks, "
                        "tight architectural coupling, and difficulty in isolated unit testing."
                    ),
                    severity=severity,
                    confidence=FindingConfidence.HIGH,
                    recommendation=(
                        "Break the cycle by extracting shared data types, interfaces, or helper functions "
                        "into a separate layer or using dependency injection."
                    ),
                    evidence=evidence_items,
                    related_entities=affected_files,
                    metadata={"cycle_length": len(affected_files), "path": affected_files},
                    score=85.0 if severity == FindingSeverity.HIGH else 65.0,
                )
            )

        return findings

    def _resolve_target_path(
        self,
        src_path: str,
        target: str,
        all_paths: set[str],
    ) -> str | None:
        cleaned_target = target.strip("'\"")

        # Direct exact match
        if cleaned_target in all_paths:
            return cleaned_target

        # Relative import resolution (e.g. ./session or ../utils)
        if cleaned_target.startswith("."):
            src_dir = posixpath.dirname(src_path)
            candidate_base = posixpath.normpath(posixpath.join(src_dir, cleaned_target))
            for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".py"):
                cand = candidate_base + ext
                if cand in all_paths:
                    return cand
            for index_file in ("/index.ts", "/index.js", "/__init__.py"):
                cand = candidate_base + index_file
                if cand in all_paths:
                    return cand

        # Python dot import (e.g. src.auth.service -> src/auth/service.py)
        dot_as_slash = cleaned_target.replace(".", "/")
        for ext in ("", ".py", ".ts", ".tsx", ".js"):
            cand = dot_as_slash + ext
            if cand in all_paths:
                return cand
            for p in all_paths:
                if p.endswith(cand) or p == f"{dot_as_slash}/__init__.py":
                    return p

        # Basename match
        base = os.path.splitext(os.path.basename(cleaned_target))[0].lower()
        for p in all_paths:
            p_base = os.path.splitext(os.path.basename(p))[0].lower()
            if p_base == base and p_base not in ("__init__", "index", "conftest"):
                return p

        return None

    def _find_cycles(
        self,
        graph: dict[str, list[tuple[str, Any]]],
    ) -> list[list[str]]:
        cycles: list[list[str]] = []
        seen_canonical: set[tuple[str, ...]] = set()

        def dfs(node: str, path: list[str], visited: set[str]) -> None:
            for neighbor, _dep in graph.get(node, []):
                if neighbor in path:
                    # Found a cycle
                    cycle_start_idx = path.index(neighbor)
                    cycle_nodes = path[cycle_start_idx:]
                    if len(cycle_nodes) >= 2:
                        # Normalize canonical representation
                        min_node = min(cycle_nodes)
                        min_idx = cycle_nodes.index(min_node)
                        canonical = tuple(cycle_nodes[min_idx:] + cycle_nodes[:min_idx])
                        if canonical not in seen_canonical:
                            seen_canonical.add(canonical)
                            cycles.append(list(canonical) + [canonical[0]])
                elif neighbor not in visited and len(path) < 10:  # Bound search depth
                    dfs(neighbor, path + [neighbor], visited | {neighbor})

        for node in list(graph.keys()):
            dfs(node, [node], {node})

        return cycles
