"""
ATOM Code Lane Quality Evaluation Dataset.

Handcrafted, manually verified ground-truth dataset representing realistic
code changes across:
1. Simple behavior changes
2. Compound changes with multiple facts
3. Function calls, imports, and symbol relationships
4. Configuration and validation changes
5. Deletions and removals
6. File renames and lineage
7. Duplicate relationships across commits
8. Changes with unknown temporal boundaries
9. Ambiguous changes with minimal evidence (uncertainty preservation)
10. Temporal conflicts (contradictory boundaries)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from apps.api.src.schemas.code_atom import (
    CodeChangeType,
    FactConfidence,
    FactType,
    GitCommitArtifact,
    GitDiffHunk,
    GitFileDiff,
    RelationType,
)


@dataclass(frozen=True)
class ExpectedFact:
    """Manually verified expected semantic atomic fact."""
    fact_type: FactType
    confidence: FactConfidence
    is_uncertain: bool
    statement_keywords: list[str]
    symbol_name: str | None = None
    evidenced_lines_contain: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExpectedRelation:
    """Manually verified expected temporal code relation."""
    subject_keyword: str
    relation: RelationType
    object_keyword: str
    has_t_start: bool = True
    has_t_end: bool = False
    has_t_obs: bool = True
    t_start: datetime | None = None
    t_end: datetime | None = None
    t_obs: datetime | None = None
    is_uncertain: bool = False
    canonical_subject_keyword: str | None = None
    canonical_object_keyword: str | None = None


@dataclass
class GroundTruthCase:
    """A single evaluation scenario with verified input diff and ground-truth outputs."""
    case_id: str
    name: str
    category: str
    commit: GitCommitArtifact
    expected_facts: list[ExpectedFact]
    expected_relations: list[ExpectedRelation]
    rename_history: dict[str, str] = field(default_factory=dict)
    second_commit: GitCommitArtifact | None = None
    expected_deduped_relation_count: int | None = None
    expected_temporal_conflicts: int = 0
    is_ambiguous: bool = False


# Base reference timestamps
T_COM_1 = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)
T_COM_2 = datetime(2026, 4, 15, 14, 30, 0, tzinfo=UTC)
T_COM_3 = datetime(2026, 5, 1, 9, 15, 0, tzinfo=UTC)


def get_ground_truth_dataset() -> list[GroundTruthCase]:
    """Returns the full collection of 10 handcrafted, verified ground-truth scenarios."""
    return [
        # 1. Simple Behavior Change (formula/return value modification)
        GroundTruthCase(
            case_id="case_01_simple_behavior",
            name="Simple Behavior Calculation Update",
            category="behavior",
            commit=GitCommitArtifact(
                commit_sha="c1_simple_behavior_sha",
                commit_message="feat(pricing): update discount multiplier to 15 percent",
                committed_at=T_COM_1,
                raw_diff="""diff --git a/apps/api/src/pricing.py b/apps/api/src/pricing.py
--- a/apps/api/src/pricing.py
+++ b/apps/api/src/pricing.py
@@ -10,3 +10,4 @@ def calculate_discount(amount: float) -> float:
-    return amount * 0.05
+    return amount * 0.15
""",
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["calculate_discount", "returns", "amount * 0.15"],
                    symbol_name="calculate_discount",
                    evidenced_lines_contain=["return amount * 0.15"],
                )
            ],
            expected_relations=[],  # No external method calls or imports
        ),

        # 2. Compound Change (Validation + State Change + Persistence)
        GroundTruthCase(
            case_id="case_02_compound_change",
            name="Compound Validation, Mutation, and Persistence",
            category="compound",
            commit=GitCommitArtifact(
                commit_sha="c2_compound_sha",
                commit_message="feat(user): validate email format, set email, and persist user",
                committed_at=T_COM_1,
                raw_diff="""diff --git a/apps/api/src/user_service.py b/apps/api/src/user_service.py
--- a/apps/api/src/user_service.py
+++ b/apps/api/src/user_service.py
@@ -20,4 +20,7 @@ def update_user_email(user_id: str, new_email: str) -> bool:
     if not new_email:
         return False
+    if "@" not in new_email:
+        raise InvalidEmailException()
+    user.set_email(new_email)
+    user_repo.save(user)
""",
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.ERROR_HANDLING,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["update_user_email", "raises", "InvalidEmailException"],
                    symbol_name="update_user_email",
                    evidenced_lines_contain=["raise InvalidEmailException()"],
                ),
                ExpectedFact(
                    fact_type=FactType.STATE_CHANGE,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["update_user_email", "updates", "email", "set_email"],
                    symbol_name="update_user_email",
                    evidenced_lines_contain=["user.set_email(new_email)"],
                ),
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["update_user_email", "persists", "user_repo", "save"],
                    symbol_name="update_user_email",
                    evidenced_lines_contain=["user_repo.save(user)"],
                ),
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="update_user_email",
                    relation=RelationType.RAISES,
                    object_keyword="InvalidEmailException",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
                ExpectedRelation(
                    subject_keyword="update_user_email",
                    relation=RelationType.MUTATES,
                    object_keyword="user",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
                ExpectedRelation(
                    subject_keyword="update_user_email",
                    relation=RelationType.CALLS,
                    object_keyword="user",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
                ExpectedRelation(
                    subject_keyword="update_user_email",
                    relation=RelationType.MUTATES,
                    object_keyword="user_repo",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
                ExpectedRelation(
                    subject_keyword="update_user_email",
                    relation=RelationType.CALLS,
                    object_keyword="user_repo",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
            ],
        ),

        # 3. External Module Import & Function Call
        GroundTruthCase(
            case_id="case_03_calls_and_imports",
            name="External HTTP Client Import and Call",
            category="relations",
            commit=GitCommitArtifact(
                commit_sha="c3_calls_imports_sha",
                commit_message="feat(weather): query external weather service via httpx",
                committed_at=T_COM_1,
                raw_diff="""diff --git a/apps/api/src/weather.py b/apps/api/src/weather.py
--- a/apps/api/src/weather.py
+++ b/apps/api/src/weather.py
@@ -1,4 +1,7 @@ def fetch_forecast():
+import httpx
+
 def fetch_forecast():
+    client.get("https://weather.example.com")
     return True
""",
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["weather.py", "imports", "httpx"],
                    evidenced_lines_contain=["import httpx"],
                ),
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["fetch_forecast", "calls", "client.get"],
                    symbol_name="fetch_forecast",
                    evidenced_lines_contain=["client.get"],
                ),
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="weather.py",
                    relation=RelationType.IMPORTS,
                    object_keyword="httpx",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
                ExpectedRelation(
                    subject_keyword="fetch_forecast",
                    relation=RelationType.CALLS,
                    object_keyword="client",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
            ],
        ),

        # 4. Configuration and Environment Settings
        GroundTruthCase(
            case_id="case_04_config_settings",
            name="YAML Service Configuration",
            category="configuration",
            commit=GitCommitArtifact(
                commit_sha="c4_config_sha",
                commit_message="chore(config): set request timeout and max retries",
                committed_at=T_COM_1,
                raw_diff="""diff --git a/apps/api/config/service.yaml b/apps/api/config/service.yaml
--- a/apps/api/config/service.yaml
+++ b/apps/api/config/service.yaml
@@ -1,2 +1,4 @@
+TIMEOUT_SECONDS: 30
+MAX_RETRIES: 3
""",
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.CONFIGURATION,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["service.yaml", "configures", "TIMEOUT_SECONDS", "30"],
                    evidenced_lines_contain=["TIMEOUT_SECONDS: 30"],
                ),
                ExpectedFact(
                    fact_type=FactType.CONFIGURATION,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["service.yaml", "configures", "MAX_RETRIES", "3"],
                    evidenced_lines_contain=["MAX_RETRIES: 3"],
                ),
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="service.yaml",
                    relation=RelationType.CONFIGURES,
                    object_keyword="TIMEOUT_SECONDS",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
                ExpectedRelation(
                    subject_keyword="service.yaml",
                    relation=RelationType.CONFIGURES,
                    object_keyword="MAX_RETRIES",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,
                    t_obs=T_COM_1,
                ),
            ],
        ),

        # 5. Logic Deletion & Cessation
        GroundTruthCase(
            case_id="case_05_deletion_cessation",
            name="Removal of Legacy Telemetry Hook",
            category="removal",
            commit=GitCommitArtifact(
                commit_sha="c5_deletion_sha",
                commit_message="refactor(audit): remove deprecated LegacyTracker invocation",
                committed_at=T_COM_2,
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/audit.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -10,3 +10,1 @@",
                                section_header="def record_audit():",
                                old_start_line=10,
                                old_line_count=3,
                                new_start_line=10,
                                new_line_count=1,
                                deleted_lines=["    LegacyTracker.record_event(payload)"],
                            )
                        ],
                    )
                ],
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.REMOVAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["record_audit", "removed logic", "LegacyTracker.record_event"],
                    symbol_name="record_audit",
                    evidenced_lines_contain=["LegacyTracker.record_event(payload)"],
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="record_audit",
                    relation=RelationType.CALLS,
                    object_keyword="LegacyTracker",
                    has_t_start=False,
                    has_t_end=True,
                    t_start=None,
                    t_end=T_COM_2,
                    t_obs=T_COM_2,
                )
            ],
        ),

        # 6. File Rename and Identity Lineage
        GroundTruthCase(
            case_id="case_06_rename_lineage",
            name="Worker File Rename with Method Preservation",
            category="rename",
            commit=GitCommitArtifact(
                commit_sha="c6_rename_sha",
                commit_message="refactor: move old_worker.py to worker.py",
                committed_at=T_COM_2,
                file_diffs=[
                    GitFileDiff(
                        old_path="apps/api/src/old_worker.py",
                        new_path="apps/api/src/worker.py",
                        change_type=CodeChangeType.RENAME,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -5,3 +5,4 @@",
                                section_header="def execute_job():",
                                old_start_line=5,
                                old_line_count=3,
                                new_start_line=5,
                                new_line_count=4,
                                added_lines=["    QueueManager.pop_item()"],
                            )
                        ],
                    )
                ],
            ),
            rename_history={"apps/api/src/old_worker.py": "apps/api/src/worker.py"},
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.STRUCTURAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["Renamed", "old_worker.py", "worker.py"],
                ),
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="execute_job",
                    relation=RelationType.CALLS,
                    object_keyword="QueueManager",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_2,
                    t_obs=T_COM_2,
                    canonical_subject_keyword="apps/api/src/worker.py::execute_job",
                )
            ],
        ),

        # 7. Duplicate Relationships Across Commits
        GroundTruthCase(
            case_id="case_07_duplicate_resolution",
            name="Cross-Commit Duplicate Relation Deduplication",
            category="deduplication",
            commit=GitCommitArtifact(
                commit_sha="c7_commit_1",
                commit_message="feat(auth): initial session token verification",
                committed_at=T_COM_1,
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/session.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -5,3 +5,5 @@",
                                section_header="def verify_session():",
                                old_start_line=5,
                                old_line_count=3,
                                new_start_line=5,
                                new_line_count=5,
                                added_lines=["    TokenService.verify(token)"],
                            )
                        ],
                    )
                ],
            ),
            second_commit=GitCommitArtifact(
                commit_sha="c7_commit_2",
                commit_message="fix(auth): reaffirm session token verification with retries",
                committed_at=T_COM_3,
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/session.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -5,4 +5,6 @@",
                                section_header="def verify_session():",
                                old_start_line=5,
                                old_line_count=4,
                                new_start_line=5,
                                new_line_count=6,
                                added_lines=["    TokenService.verify(token)"],
                            )
                        ],
                    )
                ],
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["verify_session", "calls", "TokenService.verify"],
                    symbol_name="verify_session",
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="verify_session",
                    relation=RelationType.CALLS,
                    object_keyword="TokenService",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_1,  # Preserves earliest verified start
                    t_obs=T_COM_1,
                )
            ],
            expected_deduped_relation_count=1,
        ),

        # 8. Unknown Temporal Boundaries (commit timestamp absent)
        GroundTruthCase(
            case_id="case_08_unknown_timestamps",
            name="Commit with Unspecified Timestamp",
            category="temporal",
            commit=GitCommitArtifact(
                commit_sha="c8_no_time_sha",
                commit_message="chore: update telemetry without git timestamp metadata",
                committed_at=None,  # Unknown timestamp!
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/metrics.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -1,3 +1,5 @@",
                                section_header="def emit_metric():",
                                old_start_line=1,
                                old_line_count=3,
                                new_start_line=1,
                                new_line_count=5,
                                added_lines=["    StatsdClient.increment(key)"],
                            )
                        ],
                    )
                ],
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["emit_metric", "calls", "StatsdClient.increment"],
                    symbol_name="emit_metric",
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="emit_metric",
                    relation=RelationType.CALLS,
                    object_keyword="StatsdClient",
                    has_t_start=False,
                    has_t_end=False,
                    has_t_obs=False,
                    t_start=None,
                    t_end=None,
                    t_obs=None,
                )
            ],
        ),

        # 9. Ambiguous / Minimal Evidence Change (preserves UNCERTAIN)
        GroundTruthCase(
            case_id="case_09_ambiguous_minimal_evidence",
            name="Ambiguous Variable Assignment",
            category="ambiguous",
            is_ambiguous=True,
            commit=GitCommitArtifact(
                commit_sha="c9_ambiguous_sha",
                commit_message="chore: update internal loop index",
                committed_at=T_COM_1,
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/counter.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -10,2 +10,3 @@",
                                section_header="def tick():",
                                old_start_line=10,
                                old_line_count=2,
                                new_start_line=10,
                                new_line_count=3,
                                added_lines=["    counter = 1"],
                            )
                        ],
                    )
                ],
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.UNCERTAIN,
                    is_uncertain=True,
                    statement_keywords=["tick", "assigns", "counter"],
                    symbol_name="tick",
                    evidenced_lines_contain=["counter = 1"],
                )
            ],
            expected_relations=[],  # No external relations inferred
        ),

        # 10. Temporal Conflict Detection (End before Start)
        GroundTruthCase(
            case_id="case_10_temporal_conflict",
            name="Contradictory Temporal Boundaries",
            category="temporal_conflict",
            commit=GitCommitArtifact(
                commit_sha="c10_conflict_start",
                commit_message="Introduce worker queue",
                committed_at=T_COM_2,  # Start at April 15
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/job_runner.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -1,2 +1,4 @@",
                                section_header="def run():",
                                old_start_line=1,
                                old_line_count=2,
                                new_start_line=1,
                                new_line_count=4,
                                added_lines=["    TaskQueue.push(job)"],
                            )
                        ],
                    )
                ],
            ),
            second_commit=GitCommitArtifact(
                commit_sha="c10_conflict_end",
                commit_message="Contradictory cessation at earlier date",
                committed_at=T_COM_1,  # End earlier at April 1!
                file_diffs=[
                    GitFileDiff(
                        new_path="apps/api/src/job_runner.py",
                        change_type=CodeChangeType.MODIFY,
                        hunks=[
                            GitDiffHunk(
                                header="@@ -1,4 +1,2 @@",
                                section_header="def run():",
                                old_start_line=1,
                                old_line_count=4,
                                new_start_line=1,
                                new_line_count=2,
                                deleted_lines=["    TaskQueue.push(job)"],
                            )
                        ],
                    )
                ],
            ),
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=["run", "calls", "TaskQueue.push"],
                    symbol_name="run",
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword="run",
                    relation=RelationType.CALLS,
                    object_keyword="TaskQueue",
                    has_t_start=True,
                    has_t_end=False,
                    t_start=T_COM_2,
                    t_obs=T_COM_2,
                )
            ],
            expected_temporal_conflicts=1,
        ),
    ]
