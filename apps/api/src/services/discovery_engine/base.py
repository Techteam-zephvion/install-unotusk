import abc
import posixpath
import uuid
from dataclasses import dataclass, field
from typing import Any

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol


@dataclass
class CandidateFinding:
    category: FindingCategory
    title: str
    description: str
    why_it_matters: str
    severity: FindingSeverity
    confidence: FindingConfidence
    recommendation: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class DiscoveryContext:
    project_id: uuid.UUID
    snapshot_id: uuid.UUID
    files: list[RepositoryFile]
    symbols: list[CodeSymbol]
    dependencies: list[CodeDependency]
    chunks: list[CodeChunk]

    # Precomputed lookups & indices
    file_by_id: dict[uuid.UUID, RepositoryFile] = field(default_factory=dict)
    file_by_path: dict[str, RepositoryFile] = field(default_factory=dict)
    symbols_by_file_id: dict[uuid.UUID, list[CodeSymbol]] = field(default_factory=dict)
    dependencies_by_file_id: dict[uuid.UUID, list[CodeDependency]] = field(default_factory=dict)
    inbound_deps_by_target: dict[str, list[CodeDependency]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for f in self.files:
            self.file_by_id[f.id] = f
            self.file_by_path[f.path] = f
            self.symbols_by_file_id[f.id] = []
            self.dependencies_by_file_id[f.id] = []

        for s in self.symbols:
            if s.file_id in self.symbols_by_file_id:
                self.symbols_by_file_id[s.file_id].append(s)

        for d in self.dependencies:
            if d.source_file_id in self.dependencies_by_file_id:
                self.dependencies_by_file_id[d.source_file_id].append(d)

            # Inbound target lookup
            target_key = self.get_target_for_dep(d).lower().strip()
            if target_key:
                if target_key not in self.inbound_deps_by_target:
                    self.inbound_deps_by_target[target_key] = []
                self.inbound_deps_by_target[target_key].append(d)

    def get_target_for_dep(self, dep: CodeDependency) -> str:
        if dep.target_file_id and dep.target_file_id in self.file_by_id:
            return self.file_by_id[dep.target_file_id].path
        return dep.external_package or ""

    def resolve_dep_target_path(self, dep: CodeDependency, src_path: str = "") -> str | None:
        """Resolves a dependency to an internal repository file path, or None if external."""
        if dep.target_file_id and dep.target_file_id in self.file_by_id:
            return self.file_by_id[dep.target_file_id].path

        target_raw = (dep.external_package or "").strip("'\"`")
        if not target_raw:
            return None

        # Exact match against repository paths
        if target_raw in self.file_by_path:
            return target_raw

        # Relative path resolution e.g. ./session, ../utils
        if target_raw.startswith(".") and src_path:
            src_dir = posixpath.dirname(src_path)
            candidate_base = posixpath.normpath(posixpath.join(src_dir, target_raw))
            for ext in ("", ".py", ".ts", ".tsx", ".js", ".jsx"):
                cand = candidate_base + ext
                if cand in self.file_by_path:
                    return cand
            for idx in ("/index.ts", "/index.js", "/index.tsx", "/index.jsx", "/__init__.py"):
                cand = candidate_base + idx
                if cand in self.file_by_path:
                    return cand

        # Dot-notated module import (e.g. src.auth.service -> src/auth/service.py)
        target_as_slash = target_raw.replace(".", "/")
        for p in self.file_by_path:
            p_no_ext = posixpath.splitext(p)[0]
            if (
                p == target_raw
                or p.endswith("/" + target_raw)
                or p_no_ext == target_as_slash
                or p_no_ext.endswith("/" + target_as_slash)
            ):
                return p

        return None


class DiscoveryAnalyzer(abc.ABC):
    @property
    @abc.abstractmethod
    def category(self) -> FindingCategory:
        pass

    @abc.abstractmethod
    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        pass
