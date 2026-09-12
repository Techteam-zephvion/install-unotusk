from dataclasses import dataclass, field
from typing import Any

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.discovery_run import DiscoveryRun
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.finding import Finding
from apps.api.src.models.project import Project
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol


@dataclass
class FactData:
    project: Project
    snapshot: RepositorySnapshot
    files: list[RepositoryFile]
    symbols: list[CodeSymbol]
    dependencies: list[CodeDependency]
    findings: list[Finding]
    discovery_run: DiscoveryRun | None
    language_counts: dict[str, int] = field(default_factory=dict)
    total_lines: int = 0
    total_bytes: int = 0
    file_by_id: dict[Any, RepositoryFile] = field(default_factory=dict)
    file_by_path: dict[str, RepositoryFile] = field(default_factory=dict)
    file_consumers: dict[str, set[str]] = field(default_factory=dict)
    symbol_consumers: dict[str, int] = field(default_factory=dict)
    external_packages: set[str] = field(default_factory=set)
    cycles: list[list[str]] = field(default_factory=list)
    knowledge_items: list[Any] = field(default_factory=list)
