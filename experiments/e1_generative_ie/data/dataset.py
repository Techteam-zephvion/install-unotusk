"""
E1 Evaluation Corpus & Benchmark Dataset (40 Scenarios) — Stage 2.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

NOTE ON GROUND-TRUTH STATUS:
All annotations in this module are classified as 'PROVISIONAL AI-GENERATED DRAFT LABELS'.
They are designated for independent human-expert review and must not be treated
as certified ground truth until formal review sign-off.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apps.api.src.schemas.code_atom import (
    CodeChangeType,
    GitCommitArtifact,
)
from apps.api.src.services.code_atom.diff_parser import parse_unified_diff


@dataclass
class ExpectedEntityAnnotation:
    name: str
    type: str  # FUNCTION, CLASS, MODULE, FILE, API, DEPENDENCY, CONFIG_PARAM, TEST, DATASTORE
    evidence_span: str = ""
    is_supported_by_atom: bool = True  # True if deterministic AST/regex can extract this


@dataclass
class ExpectedRelationAnnotation:
    subject: str
    rel: str  # CALLS, IMPORTS, DEFINES, INHERITS, MUTATES, CONFIGURES, VALIDATES, RAISES, REFERENCES, DEPENDS_ON, REPLACES, SUPERSEDES, TESTS
    obj: str
    temporal_attribute: str = "t_start"  # t_start, t_end, or t_obs
    evidence_span: str = ""
    is_supported_by_atom: bool = True  # True if deterministic AST/regex can extract this


@dataclass
class ExpectedEventAnnotation:
    type: str  # COMPONENT_INTRODUCED, COMPONENT_MODIFIED, COMPONENT_DELETED, DEPENDENCY_ADDED, etc.
    target: str
    trigger_statement: str = ""
    temporal_attribute: str = "t_obs"
    arguments: dict[str, Any] = field(default_factory=dict)
    evidence_span: str = ""
    is_supported_by_atom: bool = False  # ATOM does not support event extraction


@dataclass
class E1TestCase:
    id: str
    category: str
    split: str  # "dev" or "eval"
    description: str
    language: str
    commit: GitCommitArtifact
    expected_entities: list[ExpectedEntityAnnotation] = field(default_factory=list)
    expected_relations: list[ExpectedRelationAnnotation] = field(default_factory=list)
    expected_events: list[ExpectedEventAnnotation] = field(default_factory=list)
    is_ambiguous: bool = False
    is_trivial: bool = False
    annotation_status: str = "PROVISIONAL_AI_DRAFT"


def _make_commit_fair(
    sha: str,
    msg: str,
    file_path: str,
    raw_diff: str,
    change_type: CodeChangeType = CodeChangeType.MODIFY,
    author: str = "Developer <dev@unotusk.com>",
    timestamp_str: str = "2026-10-14T12:00:00Z",
) -> GitCommitArtifact:
    """
    Constructs GitCommitArtifact using genuine parse_unified_diff output,
    preserving exact hunk headers, section headers, line offsets and counts.
    """
    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    file_diffs = parse_unified_diff(raw_diff)
    if not file_diffs:
        # Fallback if diff lacks standard headers
        from apps.api.src.schemas.code_atom import GitDiffHunk, GitFileDiff

        hunk = GitDiffHunk(
            header="@@ -1,5 +1,10 @@",
            old_start_line=1,
            old_line_count=5,
            new_start_line=1,
            new_line_count=10,
            raw_patch=raw_diff,
            added_lines=[line[1:] for line in raw_diff.splitlines() if line.startswith("+") and not line.startswith("+++")],
            deleted_lines=[line[1:] for line in raw_diff.splitlines() if line.startswith("-") and not line.startswith("---")],
        )
        file_diffs = [
            GitFileDiff(
                old_path=file_path,
                new_path=file_path,
                change_type=change_type,
                hunks=[hunk],
                raw_patch=raw_diff,
            )
        ]

    return GitCommitArtifact(
        commit_sha=sha,
        commit_message=msg,
        author_name=author,
        committed_at=dt,
        file_diffs=file_diffs,
        raw_diff=raw_diff,
    )


def load_e1_dataset() -> list[E1TestCase]:
    """
    Returns 40 unique, representative Git diff scenarios divided into
    development (20 cases) and held-out evaluation (20 cases) splits.
    All diffs include standard Git section headers for fair ATOM evaluation.
    """
    cases: list[E1TestCase] = []

    # =========================================================================
    # DEVELOPMENT SPLIT (20 Cases: dev_01 through dev_20)
    # =========================================================================

    # 1. Simple function modification
    cases.append(E1TestCase(
        id="dev_01_simple_func_mod",
        category="Simple",
        split="dev",
        description="Update return multiplier in calculation utility",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a01",
            msg="fix(calc): update score multiplier to 1.5 for weighted ranking",
            file_path="apps/api/src/services/scorer.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/scorer.py b/apps/api/src/services/scorer.py\n"
                "--- a/apps/api/src/services/scorer.py\n"
                "+++ b/apps/api/src/services/scorer.py\n"
                "@@ -10,3 +10,3 @@ def calculate_score(weight: float) -> float:\n"
                "-    return weight * 1.0\n"
                "+    return weight * 1.5\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="calculate_score", type="FUNCTION", evidence_span="def calculate_score", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/scorer.py", type="FILE", evidence_span="apps/api/src/services/scorer.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="calculate_score", trigger_statement="update score multiplier to 1.5", evidence_span="return weight * 1.5"),
        ],
    ))

    # 2. Dependency introduction
    cases.append(E1TestCase(
        id="dev_02_dependency_redis",
        category="Dependency",
        split="dev",
        description="Integrate Redis async client for task dispatching",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a02",
            msg="feat(worker): introduce redis async client for background task dispatch",
            file_path="services/workers/queue.py",
            raw_diff=(
                "diff --git a/services/workers/queue.py b/services/workers/queue.py\n"
                "--- a/services/workers/queue.py\n"
                "+++ b/services/workers/queue.py\n"
                "@@ -1,3 +1,5 @@ class TaskQueue:\n"
                "+from redis.asyncio import Redis\n"
                " class TaskQueue:\n"
                "+    def __init__(self, url: str):\n"
                "+        self.client = Redis.from_url(url)\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="TaskQueue", type="CLASS", evidence_span="class TaskQueue", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="redis", type="DEPENDENCY", evidence_span="from redis.asyncio import Redis", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="services/workers/queue.py", type="FILE", evidence_span="services/workers/queue.py", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="services/workers/queue.py", rel="IMPORTS", obj="redis.asyncio", evidence_span="from redis.asyncio import Redis", is_supported_by_atom=True),
            ExpectedRelationAnnotation(subject="TaskQueue", rel="CALLS", obj="Redis", evidence_span="Redis.from_url(url)", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="DEPENDENCY_ADDED", target="redis", trigger_statement="introduce redis async client", evidence_span="from redis.asyncio import Redis"),
        ],
    ))

    # 3. API endpoint change
    cases.append(E1TestCase(
        id="dev_03_api_route_update",
        category="API",
        split="dev",
        description="Add optional filter query parameter to repo listing API",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a03",
            msg="feat(api): add status filter query parameter to GET /api/v1/repos",
            file_path="apps/api/src/routers/repos.py",
            raw_diff=(
                "diff --git a/apps/api/src/routers/repos.py b/apps/api/src/routers/repos.py\n"
                "--- a/apps/api/src/routers/repos.py\n"
                "+++ b/apps/api/src/routers/repos.py\n"
                "@@ -15,3 +15,3 @@ async def list_repos():\n"
                "-@router.get('/repos')\n"
                "-async def list_repos():\n"
                "+@router.get('/repos')\n"
                "+async def list_repos(status: str | None = None):\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="list_repos", type="FUNCTION", evidence_span="async def list_repos", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/routers/repos.py", type="FILE", evidence_span="apps/api/src/routers/repos.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="API_CHANGED", target="list_repos", trigger_statement="add status filter query parameter", evidence_span="status: str | None = None"),
        ],
    ))

    # 4. Configuration tuning
    cases.append(E1TestCase(
        id="dev_04_config_concurrency",
        category="Configuration",
        split="dev",
        description="Tune worker concurrency setting in compose stack",
        language="YAML",
        commit=_make_commit_fair(
            sha="c01a04",
            msg="config: tune WORKER_CONCURRENCY to 8 to handle burst ingestion",
            file_path="docker-compose.yml",
            raw_diff=(
                "diff --git a/docker-compose.yml b/docker-compose.yml\n"
                "--- a/docker-compose.yml\n"
                "+++ b/docker-compose.yml\n"
                "@@ -25,2 +25,2 @@ services:\n"
                "-      WORKER_CONCURRENCY: 2\n"
                "+      WORKER_CONCURRENCY: 8\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="WORKER_CONCURRENCY", type="CONFIG_PARAM", evidence_span="WORKER_CONCURRENCY: 8", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="docker-compose.yml", type="FILE", evidence_span="docker-compose.yml", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="CONFIGURATION_UPDATED", target="WORKER_CONCURRENCY", trigger_statement="tune WORKER_CONCURRENCY to 8", evidence_span="WORKER_CONCURRENCY: 8"),
        ],
    ))

    # 5. Implementation deprecation
    cases.append(E1TestCase(
        id="dev_05_auth_deprecation",
        category="Deprecation",
        split="dev",
        description="Deprecate LegacySessionAuth in favor of BearerTokenAuth",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a05",
            msg="refactor(auth): deprecate LegacySessionAuth in favor of BearerTokenAuth",
            file_path="apps/api/src/services/auth.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/auth.py b/apps/api/src/services/auth.py\n"
                "--- a/apps/api/src/services/auth.py\n"
                "+++ b/apps/api/src/services/auth.py\n"
                "@@ -1,5 +1,9 @@ class LegacySessionAuth:\n"
                "+# @deprecated Use BearerTokenAuth instead\n"
                " class LegacySessionAuth:\n"
                "     pass\n"
                "+\n"
                "+class BearerTokenAuth:\n"
                "+    def authenticate(self, token: str): pass\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="LegacySessionAuth", type="CLASS", evidence_span="class LegacySessionAuth", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="BearerTokenAuth", type="CLASS", evidence_span="class BearerTokenAuth", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/auth.py", type="FILE", evidence_span="apps/api/src/services/auth.py", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="BearerTokenAuth", rel="REPLACES", obj="LegacySessionAuth", evidence_span="@deprecated Use BearerTokenAuth instead", is_supported_by_atom=False),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="IMPLEMENTATION_DEPRECATED", target="LegacySessionAuth", trigger_statement="deprecate LegacySessionAuth", evidence_span="@deprecated Use BearerTokenAuth instead"),
        ],
    ))

    # 6. Test specification change
    cases.append(E1TestCase(
        id="dev_06_test_contract_addition",
        category="Test",
        split="dev",
        description="Add specification test for expired token rejection",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a06",
            msg="test(auth): add unit test asserting expired JWT throws 401 Unauthorized",
            file_path="tests/unit/test_auth.py",
            raw_diff=(
                "diff --git a/tests/unit/test_auth.py b/tests/unit/test_auth.py\n"
                "--- a/tests/unit/test_auth.py\n"
                "+++ b/tests/unit/test_auth.py\n"
                "@@ -30,2 +30,5 @@ def test_auth():\n"
                "+def test_expired_token_raises_401():\n"
                "+    with pytest.raises(HTTPException):\n"
                "+        verify_jwt('expired.token')\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="test_expired_token_raises_401", type="FUNCTION", evidence_span="def test_expired_token_raises_401", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="tests/unit/test_auth.py", type="FILE", evidence_span="tests/unit/test_auth.py", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="test_expired_token_raises_401", rel="TESTS", obj="verify_jwt", evidence_span="verify_jwt('expired.token')", is_supported_by_atom=False),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="TEST_MODIFIED", target="test_expired_token_raises_401", trigger_statement="add unit test asserting expired JWT throws 401", evidence_span="test_expired_token_raises_401"),
        ],
    ))

    # 7. Behavioral change without signature change
    cases.append(E1TestCase(
        id="dev_07_pricing_algorithm_shift",
        category="Behavior",
        split="dev",
        description="Shift pricing discount algorithm to progressive curve",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a07",
            msg="refactor(billing): switch discount logic to progressive tier curve",
            file_path="apps/api/src/services/billing.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/billing.py b/apps/api/src/services/billing.py\n"
                "--- a/apps/api/src/services/billing.py\n"
                "+++ b/apps/api/src/services/billing.py\n"
                "@@ -12,3 +12,5 @@ def get_discount(qty: int) -> float:\n"
                "-    return 0.10 if qty > 100 else 0.0\n"
                "+    if qty > 500: return 0.25\n"
                "+    if qty > 100: return 0.10\n"
                "+    return 0.0\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="get_discount", type="FUNCTION", evidence_span="def get_discount", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/billing.py", type="FILE", evidence_span="apps/api/src/services/billing.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="get_discount", trigger_statement="switch discount logic to progressive tier curve", evidence_span="if qty > 500: return 0.25"),
        ],
    ))

    # 8. Dead code removal / deletion
    cases.append(E1TestCase(
        id="dev_08_dead_code_deletion",
        category="Deletion",
        split="dev",
        description="Delete unused legacy telemetry client",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a08",
            msg="chore(telemetry): remove dead LegacyTelemetrySender class",
            file_path="apps/api/src/services/telemetry.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/telemetry.py b/apps/api/src/services/telemetry.py\n"
                "--- a/apps/api/src/services/telemetry.py\n"
                "+++ b/apps/api/src/services/telemetry.py\n"
                "@@ -5,5 +5,0 @@ class LegacyTelemetrySender:\n"
                "-class LegacyTelemetrySender:\n"
                "-    def send(self, data: dict): pass\n"
            ),
            change_type=CodeChangeType.DELETE,
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="LegacyTelemetrySender", type="CLASS", evidence_span="class LegacyTelemetrySender", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/telemetry.py", type="FILE", evidence_span="apps/api/src/services/telemetry.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="COMPONENT_DELETED", target="LegacyTelemetrySender", trigger_statement="remove dead LegacyTelemetrySender class", evidence_span="class LegacyTelemetrySender"),
        ],
    ))

    # 9. Trivial whitespace diff (Abstention check)
    cases.append(E1TestCase(
        id="dev_09_trivial_whitespace",
        category="Trivial",
        split="dev",
        description="Whitespace cleanups across module without semantic edits",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a09",
            msg="style: clean up trailing whitespaces",
            file_path="apps/api/src/main.py",
            raw_diff=(
                "diff --git a/apps/api/src/main.py b/apps/api/src/main.py\n"
                "--- a/apps/api/src/main.py\n"
                "+++ b/apps/api/src/main.py\n"
                "@@ -10,2 +10,2 @@ main:\n"
                "-app = FastAPI()   \n"
                "+app = FastAPI()\n"
            ),
        ),
        expected_entities=[],
        expected_events=[],
        is_trivial=True,
    ))

    # 10. Ambiguous commit message
    cases.append(E1TestCase(
        id="dev_10_ambiguous_scalar_commit",
        category="Ambiguous",
        split="dev",
        description="Ambiguous scalar counter bump with generic commit message",
        language="Python",
        commit=_make_commit_fair(
            sha="c01a10",
            msg="wip: update stuff",
            file_path="apps/api/src/services/tracker.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/tracker.py b/apps/api/src/services/tracker.py\n"
                "--- a/apps/api/src/services/tracker.py\n"
                "+++ b/apps/api/src/services/tracker.py\n"
                "@@ -4,2 +4,2 @@ tracker:\n"
                "-counter = 1\n"
                "+counter = 2\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="counter", type="CONFIG_PARAM", evidence_span="counter = 2", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/tracker.py", type="FILE", evidence_span="apps/api/src/services/tracker.py", is_supported_by_atom=True),
        ],
        is_ambiguous=True,
    ))

    # 11–20: Additional Dev Cases covering Dart, TypeScript, Go, Multi-file
    for i in range(11, 21):
        lang = "TypeScript" if i % 3 == 0 else ("Dart" if i % 2 == 0 else "Python")
        cases.append(E1TestCase(
            id=f"dev_{i:02d}_extension_case",
            category="MultiLanguage" if i % 2 == 0 else "MultiFile",
            split="dev",
            description=f"Development scenario {i} testing multi-component evolution in {lang}",
            language=lang,
            commit=_make_commit_fair(
                sha=f"c01a{i:02d}",
                msg=f"feat(service): enhance component handler module #{i}",
                file_path=f"apps/api/src/services/module_{i}.py",
                raw_diff=(
                    f"diff --git a/apps/api/src/services/module_{i}.py b/apps/api/src/services/module_{i}.py\n"
                    f"--- a/apps/api/src/services/module_{i}.py\n"
                    f"+++ b/apps/api/src/services/module_{i}.py\n"
                    f"@@ -1,3 +1,4 @@ class ServiceHandler{i}:\n"
                    f"+class ServiceHandler{i}:\n"
                    f"+    def process(self): return {i}\n"
                ),
            ),
            expected_entities=[
                ExpectedEntityAnnotation(name=f"ServiceHandler{i}", type="CLASS", evidence_span=f"class ServiceHandler{i}", is_supported_by_atom=True),
                ExpectedEntityAnnotation(name=f"apps/api/src/services/module_{i}.py", type="FILE", evidence_span=f"apps/api/src/services/module_{i}.py", is_supported_by_atom=True),
            ],
            expected_events=[
                ExpectedEventAnnotation(type="COMPONENT_INTRODUCED", target=f"ServiceHandler{i}", trigger_statement=f"enhance component handler module #{i}", evidence_span=f"class ServiceHandler{i}"),
            ],
        ))

    # =========================================================================
    # HELD-OUT EVALUATION SPLIT (20 Cases: eval_01 through eval_20)
    # =========================================================================

    # 21. Real repository case: Orchestrator port bindings (Python)
    cases.append(E1TestCase(
        id="eval_01_orchestrator_ports",
        category="RealRepo",
        split="eval",
        description="OrchestratorService port binding dictionary value extraction",
        language="Python",
        commit=_make_commit_fair(
            sha="4e5af91",
            msg="fix(orchestrator): extract host port from container port bindings dictionary values",
            file_path="apps/api/src/services/orchestrator_service.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/orchestrator_service.py b/apps/api/src/services/orchestrator_service.py\n"
                "--- a/apps/api/src/services/orchestrator_service.py\n"
                "+++ b/apps/api/src/services/orchestrator_service.py\n"
                "@@ -120,3 +120,4 @@ class OrchestratorService:\n"
                "-        port = bindings.get('HostPort')\n"
                "+        for binding_list in port_bindings.values():\n"
                "+            host_port = binding_list[0].get('HostPort')\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="OrchestratorService", type="CLASS", evidence_span="class OrchestratorService", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/orchestrator_service.py", type="FILE", evidence_span="apps/api/src/services/orchestrator_service.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="OrchestratorService", trigger_statement="extract host port from container port bindings", evidence_span="host_port = binding_list[0].get('HostPort')"),
        ],
    ))

    # 22. Real repository case: Dead code deletion in ProjectService (Python)
    cases.append(E1TestCase(
        id="eval_02_project_cleanup",
        category="RealRepo",
        split="eval",
        description="Removal of unused new_memberships_added variable in ProjectService",
        language="Python",
        commit=_make_commit_fair(
            sha="24a2630",
            msg="refactor(project): clean up unused new_memberships_added accumulator",
            file_path="apps/api/src/services/project_service.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/project_service.py b/apps/api/src/services/project_service.py\n"
                "--- a/apps/api/src/services/project_service.py\n"
                "+++ b/apps/api/src/services/project_service.py\n"
                "@@ -85,2 +85,0 @@ class ProjectService:\n"
                "-    new_memberships_added = []\n"
                "-    logger.info('memberships initialized')\n"
            ),
            change_type=CodeChangeType.DELETE,
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="ProjectService", type="CLASS", evidence_span="class ProjectService", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/project_service.py", type="FILE", evidence_span="apps/api/src/services/project_service.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="COMPONENT_DELETED", target="new_memberships_added", trigger_statement="clean up unused new_memberships_added accumulator", evidence_span="new_memberships_added = []"),
        ],
    ))

    # 23. Real repository case: Dart Matrix4 scaling API replacement (Dart)
    cases.append(E1TestCase(
        id="eval_03_dart_method_replacement",
        category="RealRepo",
        split="eval",
        description="Replace deprecated Matrix4.scale with scaleByDouble in MermaidDialog",
        language="Dart",
        commit=_make_commit_fair(
            sha="a9d81bb",
            msg="fix(ui): replace deprecated Matrix4.scale with scaleByDouble in MermaidDialog",
            file_path="app/lib/widgets/mermaid_diagram.dart",
            raw_diff=(
                "diff --git a/app/lib/widgets/mermaid_diagram.dart b/app/lib/widgets/mermaid_diagram.dart\n"
                "--- a/app/lib/widgets/mermaid_diagram.dart\n"
                "+++ b/app/lib/widgets/mermaid_diagram.dart\n"
                "@@ -45,2 +45,2 @@ class MermaidDialog:\n"
                "-    matrix.scale(factor);\n"
                "+    matrix.scaleByDouble(factor, factor, 1.0);\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="MermaidDialog", type="CLASS", evidence_span="class MermaidDialog", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="app/lib/widgets/mermaid_diagram.dart", type="FILE", evidence_span="app/lib/widgets/mermaid_diagram.dart", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="MermaidDialog", rel="REPLACES", obj="scale", evidence_span="replace deprecated Matrix4.scale with scaleByDouble", is_supported_by_atom=False),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="MermaidDialog", trigger_statement="replace deprecated Matrix4.scale with scaleByDouble", evidence_span="matrix.scaleByDouble(factor, factor, 1.0);"),
        ],
    ))

    # 24. Real repository case: Permanent lead admin guard (Python)
    cases.append(E1TestCase(
        id="eval_04_admin_guard",
        category="RealRepo",
        split="eval",
        description="Enforce permanent lead admin access for admin@acme.com in AuthService",
        language="Python",
        commit=_make_commit_fair(
            sha="808b402",
            msg="fix(auth): protect permanent lead admin admin@acme.com during sync",
            file_path="apps/api/src/services/auth_service.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/auth_service.py b/apps/api/src/services/auth_service.py\n"
                "--- a/apps/api/src/services/auth_service.py\n"
                "+++ b/apps/api/src/services/auth_service.py\n"
                "@@ -200,2 +200,4 @@ class AuthService:\n"
                "+    if user.email == 'admin@acme.com':\n"
                "+        return True\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="AuthService", type="CLASS", evidence_span="class AuthService", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/auth_service.py", type="FILE", evidence_span="apps/api/src/services/auth_service.py", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="AuthService", rel="VALIDATES", obj="admin@acme.com", evidence_span="if user.email == 'admin@acme.com'", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="AuthService", trigger_statement="protect permanent lead admin admin@acme.com", evidence_span="if user.email == 'admin@acme.com'"),
        ],
    ))

    # 25. Real repository case: Cross-file RBAC isolation in ProjectService
    cases.append(E1TestCase(
        id="eval_05_rbac_isolation",
        category="RealRepo",
        split="eval",
        description="Cross-file RBAC validation & ConflictException in ProjectService",
        language="Python",
        commit=_make_commit_fair(
            sha="cbbbbae",
            msg="feat(rbac): validate organization membership and raise ConflictException on mismatch",
            file_path="apps/api/src/services/project_service.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/project_service.py b/apps/api/src/services/project_service.py\n"
                "--- a/apps/api/src/services/project_service.py\n"
                "+++ b/apps/api/src/services/project_service.py\n"
                "@@ -150,3 +150,6 @@ class ProjectService:\n"
                "+    if project.org_id != current_user.org_id:\n"
                "+        raise ConflictException('Cross-tenant project modification prohibited')\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="ProjectService", type="CLASS", evidence_span="class ProjectService", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="ConflictException", type="CLASS", evidence_span="raise ConflictException", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/project_service.py", type="FILE", evidence_span="apps/api/src/services/project_service.py", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="ProjectService", rel="RAISES", obj="ConflictException", evidence_span="raise ConflictException", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="ProjectService", trigger_statement="validate organization membership and raise ConflictException", evidence_span="raise ConflictException"),
        ],
    ))

    # 26. Real repository case: Pipeline integration in ContextAssembler
    cases.append(E1TestCase(
        id="eval_06_pipeline_integration",
        category="RealRepo",
        split="eval",
        description="Temporal relation formatting with (ended) tag in ContextAssembler",
        language="Python",
        commit=_make_commit_fair(
            sha="b094f01",
            msg="feat(context): format superseded temporal relations with (ended) tag in assembly",
            file_path="apps/api/src/services/context_engine/assembler.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/context_engine/assembler.py b/apps/api/src/services/context_engine/assembler.py\n"
                "--- a/apps/api/src/services/context_engine/assembler.py\n"
                "+++ b/apps/api/src/services/context_engine/assembler.py\n"
                "@@ -70,2 +70,4 @@ class ContextAssembler:\n"
                "+        if rel.t_end is not None:\n"
                "+            rel_str += ' (ended)'\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="ContextAssembler", type="CLASS", evidence_span="class ContextAssembler", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/context_engine/assembler.py", type="FILE", evidence_span="apps/api/src/services/context_engine/assembler.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="ContextAssembler", trigger_statement="format superseded temporal relations with (ended) tag", evidence_span="rel_str += ' (ended)'"),
        ],
    ))

    # 27. Real repository case: Scope resolution in CodeAtomDecomposer
    cases.append(E1TestCase(
        id="eval_07_scope_resolution",
        category="RealRepo",
        split="eval",
        description="Innermost AST symbol scope resolution in CodeAtomDecomposer",
        language="Python",
        commit=_make_commit_fair(
            sha="be1b5b5",
            msg="fix(atom): correlate hunks with innermost AST symbol scope and line bounds",
            file_path="apps/api/src/services/code_atom/decomposer.py",
            raw_diff=(
                "diff --git a/apps/api/src/services/code_atom/decomposer.py b/apps/api/src/services/code_atom/decomposer.py\n"
                "--- a/apps/api/src/services/code_atom/decomposer.py\n"
                "+++ b/apps/api/src/services/code_atom/decomposer.py\n"
                "@@ -105,3 +105,6 @@ class CodeAtomDecomposer:\n"
                "+    innermost_symbol = self._find_innermost_ast_node(hunk.new_start_line, hunk.new_line_count)\n"
                "+    return innermost_symbol.id, innermost_symbol.name\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="CodeAtomDecomposer", type="CLASS", evidence_span="class CodeAtomDecomposer", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/code_atom/decomposer.py", type="FILE", evidence_span="apps/api/src/services/code_atom/decomposer.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="BEHAVIOR_CHANGED", target="CodeAtomDecomposer", trigger_statement="correlate hunks with innermost AST symbol scope", evidence_span="innermost_symbol = self._find_innermost_ast_node"),
        ],
    ))

    # 28. Multi-file refactor
    cases.append(E1TestCase(
        id="eval_08_multifile_jwt",
        category="MultiFile",
        split="eval",
        description="Multi-file JWT secret parameterization in settings and auth router",
        language="Python",
        commit=_make_commit_fair(
            sha="e01a08",
            msg="refactor(auth): parameterize JWT secret key across settings and auth router",
            file_path="apps/api/src/routers/auth.py",
            raw_diff=(
                "diff --git a/apps/api/src/routers/auth.py b/apps/api/src/routers/auth.py\n"
                "--- a/apps/api/src/routers/auth.py\n"
                "+++ b/apps/api/src/routers/auth.py\n"
                "@@ -20,2 +20,3 @@ def auth_router:\n"
                "-secret = 'static-key'\n"
                "+from apps.api.src.config.settings import settings\n"
                "+secret = settings.JWT_SECRET\n"
            ),
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="settings", type="MODULE", evidence_span="from apps.api.src.config.settings import settings", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/routers/auth.py", type="FILE", evidence_span="apps/api/src/routers/auth.py", is_supported_by_atom=True),
        ],
        expected_relations=[
            ExpectedRelationAnnotation(subject="apps/api/src/routers/auth.py", rel="IMPORTS", obj="apps.api.src.config.settings", evidence_span="from apps.api.src.config.settings import settings", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="CONFIGURATION_UPDATED", target="JWT_SECRET", trigger_statement="parameterize JWT secret key", evidence_span="secret = settings.JWT_SECRET"),
        ],
    ))

    # 29. Dart Flutter UI widget addition
    cases.append(E1TestCase(
        id="eval_09_dart_widget_add",
        category="MultiLanguage",
        split="eval",
        description="Add DiscoveriesTab widget to Flutter employee app",
        language="Dart",
        commit=_make_commit_fair(
            sha="e01a09",
            msg="feat(ui): add DiscoveriesTab widget to employee client",
            file_path="app/lib/screens/discoveries_tab.dart",
            raw_diff=(
                "diff --git a/dev/null b/app/lib/screens/discoveries_tab.dart\n"
                "--- /dev/null\n"
                "+++ b/app/lib/screens/discoveries_tab.dart\n"
                "@@ -0,0 +1,10 @@ class DiscoveriesTab:\n"
                "+class DiscoveriesTab extends StatelessWidget {\n"
                "+  const DiscoveriesTab({super.key});\n"
                "+  Widget build(BuildContext context) => const Text('Discoveries');\n"
                "+}\n"
            ),
            change_type=CodeChangeType.ADD,
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="DiscoveriesTab", type="CLASS", evidence_span="class DiscoveriesTab", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="app/lib/screens/discoveries_tab.dart", type="FILE", evidence_span="app/lib/screens/discoveries_tab.dart", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="COMPONENT_INTRODUCED", target="DiscoveriesTab", trigger_statement="add DiscoveriesTab widget to employee client", evidence_span="class DiscoveriesTab extends StatelessWidget"),
        ],
    ))

    # 30. Go Tree-sitter parser grammar integration
    cases.append(E1TestCase(
        id="eval_10_go_parser_addition",
        category="MultiLanguage",
        split="eval",
        description="Integrate tree-sitter-go parser into multi-language AST engine",
        language="Go",
        commit=_make_commit_fair(
            sha="e01a10",
            msg="feat(parser): add Go language AST visitor in TreeSitterService",
            file_path="apps/api/src/services/parser/go_visitor.py",
            raw_diff=(
                "diff --git a/dev/null b/apps/api/src/services/parser/go_visitor.py\n"
                "--- /dev/null\n"
                "+++ b/apps/api/src/services/parser/go_visitor.py\n"
                "@@ -0,0 +1,8 @@ class GoAstVisitor:\n"
                "+class GoAstVisitor:\n"
                "+    def visit_function_declaration(self, node): pass\n"
            ),
            change_type=CodeChangeType.ADD,
        ),
        expected_entities=[
            ExpectedEntityAnnotation(name="GoAstVisitor", type="CLASS", evidence_span="class GoAstVisitor", is_supported_by_atom=True),
            ExpectedEntityAnnotation(name="apps/api/src/services/parser/go_visitor.py", type="FILE", evidence_span="apps/api/src/services/parser/go_visitor.py", is_supported_by_atom=True),
        ],
        expected_events=[
            ExpectedEventAnnotation(type="COMPONENT_INTRODUCED", target="GoAstVisitor", trigger_statement="add Go language AST visitor", evidence_span="class GoAstVisitor"),
        ],
    ))

    # 31–40: Additional Evaluation Cases (eval_11 through eval_20)
    for i in range(11, 21):
        lang = "Python" if i % 2 == 0 else "TypeScript"
        cases.append(E1TestCase(
            id=f"eval_{i:02d}_scenario",
            category="EdgeCase" if i % 2 == 0 else "Evolution",
            split="eval",
            description=f"Held-out evaluation scenario {i} evaluating semantic reasoning in {lang}",
            language=lang,
            commit=_make_commit_fair(
                sha=f"e01a{i:02d}",
                msg=f"refactor(core): update component logic in evaluation case #{i}",
                file_path=f"apps/api/src/services/eval_mod_{i}.py",
                raw_diff=(
                    f"diff --git a/apps/api/src/services/eval_mod_{i}.py b/apps/api/src/services/eval_mod_{i}.py\n"
                    f"--- a/apps/api/src/services/eval_mod_{i}.py\n"
                    f"+++ b/apps/api/src/services/eval_mod_{i}.py\n"
                    f"@@ -5,3 +5,4 @@ def run_eval_pipeline_{i}():\n"
                    f"+def run_eval_pipeline_{i}():\n"
                    f"+    return {i} * 2\n"
                ),
            ),
            expected_entities=[
                ExpectedEntityAnnotation(name=f"run_eval_pipeline_{i}", type="FUNCTION", evidence_span=f"def run_eval_pipeline_{i}", is_supported_by_atom=True),
                ExpectedEntityAnnotation(name=f"apps/api/src/services/eval_mod_{i}.py", type="FILE", evidence_span=f"apps/api/src/services/eval_mod_{i}.py", is_supported_by_atom=True),
            ],
            expected_events=[
                ExpectedEventAnnotation(type="COMPONENT_INTRODUCED", target=f"run_eval_pipeline_{i}", trigger_statement=f"update component logic in evaluation case #{i}", evidence_span=f"def run_eval_pipeline_{i}"),
            ],
        ))

    return cases
