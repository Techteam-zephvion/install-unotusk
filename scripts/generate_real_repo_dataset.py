"""
scripts/generate_real_repo_dataset.py

Generates `tests/fixtures/atom_real_repo_dataset.py` from genuine Git commits
in the current repository with verified ground-truth semantic facts and relations.
"""

import subprocess

cases_meta = [
    {
        "case_id": "real_01_method_call",
        "category": "method_call",
        "description": "Method call update in OrchestratorService port extraction",
        "sha": "4e5af911a97f098ac816c93a23caeb562ca007fb",
        "paths": ["apps/api/src/services/orchestrator_service.py"],
        "query": "How are host port bindings extracted in OrchestratorService?",
        "targets": ["apps/api/src/services/orchestrator_service.py", "OrchestratorService"],
        "expected_files": ["apps/api/src/services/orchestrator_service.py"],
        "expected_symbols": ["OrchestratorService"],
        "fact_type": "BEHAVIOR",
        "fact_conf": "UNCERTAIN",
        "fact_unc": True,
        "fact_kw": ["port_bindings", "values"],
        "rel_subj": "OrchestratorService",
        "rel_type": "CALLS",
        "rel_obj": "port_bindings",
        "rel_t_start": True,
        "rel_t_end": True,
    },
    {
        "case_id": "real_02_removal",
        "category": "removal",
        "description": "Dead code removal of new_memberships_added in ProjectService",
        "sha": "24a2630c9e8d213fa85a98624630da9c9c15159d",
        "paths": ["apps/api/src/services/project_service.py"],
        "query": "Where was unused new_memberships_added removed from project member synchronization?",
        "targets": ["apps/api/src/services/project_service.py", "ProjectService"],
        "expected_files": ["apps/api/src/services/project_service.py"],
        "expected_symbols": ["ProjectService"],
        "fact_type": "REMOVAL",
        "fact_conf": "HIGH",
        "fact_unc": False,
        "fact_kw": ["new_memberships_added"],
        "rel_subj": "ProjectService",
        "rel_type": "REFERENCES",
        "rel_obj": "logic",
        "rel_t_start": False,
        "rel_t_end": True,
    },
    {
        "case_id": "real_03_method_replacement",
        "category": "method_replacement",
        "description": "Replaced deprecated Matrix4.scale with scaleByDouble in Mermaid diagram",
        "sha": "a9d81bbb74279e12121243f44cd11dfdaf28a794",
        "paths": ["app/lib/widgets/mermaid_diagram.dart"],
        "query": "How is matrix scaling implemented in the mermaid diagram fullscreen dialog?",
        "targets": ["app/lib/widgets/mermaid_diagram.dart", "_MermaidFullscreenDialogState"],
        "expected_files": ["app/lib/widgets/mermaid_diagram.dart"],
        "expected_symbols": ["_MermaidFullscreenDialogState"],
        "fact_type": "BEHAVIOR",
        "fact_conf": "UNCERTAIN",
        "fact_unc": True,
        "fact_kw": ["scalebydouble"],
        "rel_subj": "_MermaidFullscreenDialogState",
        "rel_type": "CALLS",
        "rel_obj": "matrix",
        "rel_t_start": True,
        "rel_t_end": True,
    },
    {
        "case_id": "real_04_imports_refactor",
        "category": "imports_refactor",
        "description": "Added func import to sqlalchemy in auth_service for query optimization",
        "sha": "356d19b536c9cc9e147392c59427a3936b135a17",
        "paths": ["apps/api/src/services/auth_service.py"],
        "query": "Which module imports sqlalchemy func for case-insensitive email queries in auth?",
        "targets": ["apps/api/src/services/auth_service.py"],
        "expected_files": ["apps/api/src/services/auth_service.py"],
        "expected_symbols": [],
        "fact_type": "RELATIONSHIP",
        "fact_conf": "HIGH",
        "fact_unc": False,
        "fact_kw": ["sqlalchemy"],
        "rel_subj": "auth_service",
        "rel_type": "IMPORTS",
        "rel_obj": "sqlalchemy",
        "rel_t_start": True,
        "rel_t_end": True,
    },
    {
        "case_id": "real_05_configuration",
        "category": "configuration",
        "description": "Platform environment and web guard check in ApiService",
        "sha": "5526ed5578676fa515ec9a88f41844454278449f",
        "paths": ["app/lib/services/api_service.dart"],
        "query": "What is the configured port or test environment check in ApiService?",
        "targets": ["app/lib/services/api_service.dart", "ApiService"],
        "expected_files": ["app/lib/services/api_service.dart"],
        "expected_symbols": ["ApiService"],
        "fact_type": "BEHAVIOR",
        "fact_conf": "UNCERTAIN",
        "fact_unc": True,
        "fact_kw": ["environment"],
        "rel_subj": "ApiService",
        "rel_type": "CALLS",
        "rel_obj": "environment",
        "rel_t_start": True,
        "rel_t_end": True,
    },
    {
        "case_id": "real_06_admin_guard",
        "category": "admin_guard",
        "description": "Permanent lead admin assignment in AuthService for admin@acme.com",
        "sha": "808b4021451d50c4dead63db45fc606f078608a9",
        "paths": ["apps/api/src/services/auth_service.py"],
        "query": "How does AuthService assign the ADMIN role permanently to admin@acme.com?",
        "targets": ["apps/api/src/services/auth_service.py", "AuthService"],
        "expected_files": ["apps/api/src/services/auth_service.py"],
        "expected_symbols": ["AuthService"],
        "fact_type": "BEHAVIOR",
        "fact_conf": "UNCERTAIN",
        "fact_unc": True,
        "fact_kw": ["admin@acme.com"],
        "rel_subj": None,
        "rel_type": "CALLS",
        "rel_obj": None,
        "rel_t_start": False,
        "rel_t_end": False,
    },
    {
        "case_id": "real_07_rbac_isolation",
        "category": "rbac_isolation",
        "description": "Enforce organization isolation and ConflictException when adding project members",
        "sha": "cbbbbae8731ceb7e8532f58d71bff757ea3789bb",
        "paths": ["apps/api/src/services/project_service.py"],
        "query": "Where does ProjectService validate organization membership before adding a member to a project?",
        "targets": ["apps/api/src/services/project_service.py", "ProjectService"],
        "expected_files": ["apps/api/src/services/project_service.py"],
        "expected_symbols": ["ProjectService"],
        "fact_type": "ERROR_HANDLING",
        "fact_conf": "HIGH",
        "fact_unc": False,
        "fact_kw": ["conflictexception"],
        "rel_subj": "ProjectService",
        "rel_type": "RAISES",
        "rel_obj": "ConflictException",
        "rel_t_start": True,
        "rel_t_end": False,
    },
    {
        "case_id": "real_08_file_rename",
        "category": "file_rename",
        "description": "Workflow rename from build.yml to release.yml",
        "sha": "6f7570fc92a9fcf0645ee94b86d3d861c3b161e5",
        "paths": [".github/workflows/build.yml", ".github/workflows/release.yml"],
        "query": "Which GitHub workflow file handles release builds after decoupling from build.yml?",
        "targets": [".github/workflows/release.yml"],
        "expected_files": [".github/workflows/release.yml"],
        "expected_symbols": [],
        "fact_type": "STRUCTURAL",
        "fact_conf": "HIGH",
        "fact_unc": False,
        "fact_kw": ["release.yml", "build.yml"],
        "rel_subj": None,
        "rel_type": "DEFINES",
        "rel_obj": None,
        "rel_t_start": False,
        "rel_t_end": False,
        "rename_history": {".github/workflows/build.yml": ".github/workflows/release.yml"},
    },
    {
        "case_id": "real_09_pipeline_integration",
        "category": "pipeline_integration",
        "description": "ContextAssembler formatting of temporal relations with ended tag",
        "sha": "b094f015541718f5cec08f092f004a0fc6c3aa63",
        "paths": ["apps/api/src/services/context_engine/assembler.py"],
        "query": "How does ContextAssembler format temporal relationships and conflict warnings in prompt context?",
        "targets": ["apps/api/src/services/context_engine/assembler.py", "ContextAssembler"],
        "expected_files": ["apps/api/src/services/context_engine/assembler.py"],
        "expected_symbols": ["ContextAssembler"],
        "fact_type": "RELATIONSHIP",
        "fact_conf": "HIGH",
        "fact_unc": False,
        "fact_kw": ["rel_lines", "append"],
        "rel_subj": "ContextAssembler",
        "rel_type": "CALLS",
        "rel_obj": "rel_lines",
        "rel_t_start": True,
        "rel_t_end": True,
    },
    {
        "case_id": "real_10_scope_resolution",
        "category": "scope_resolution",
        "description": "CodeAtomDecomposer AST line bound resolution with innermost scope preference",
        "sha": "be1b5b5c2a96fdef91b571e3d32f9f587c4d4ed8",
        "paths": ["apps/api/src/services/code_atom/decomposer.py"],
        "query": "Where is AST symbol catalog correlation and innermost scope resolution implemented for diff hunks?",
        "targets": ["apps/api/src/services/code_atom/decomposer.py", "CodeAtomDecomposer"],
        "expected_files": ["apps/api/src/services/code_atom/decomposer.py"],
        "expected_symbols": ["CodeAtomDecomposer"],
        "fact_type": "STRUCTURAL",
        "fact_conf": "HIGH",
        "fact_unc": False,
        "fact_kw": ["candidate_symbols"],
        "rel_subj": "CodeAtomDecomposer",
        "rel_type": "CALLS",
        "rel_obj": "candidate_symbols",
        "rel_t_start": True,
        "rel_t_end": False,
    },
]

header = '''"""
ATOM Real-Repository Evaluation Dataset (Phase 14).

Curated from genuine git commits in `Techteam-zephvion/install-unotusk`:
1. Method Call Modification (OrchestratorService port extraction)
2. Dead Code Removal (ProjectService unused variable)
3. Deprecated Method Replacement (Mermaid diagram Matrix4.scaleByDouble)
4. Imports and Query Refactor (AuthService func import)
5. Configuration and Env Tuning (ApiService default port 28000)
6. Admin Privilege Guard (AuthService lead admin permanent access)
7. Multi-File RBAC & Org Isolation (ProjectService member sync)
8. Verified File Rename Lineage (build.yml -> release.yml)
9. Pipeline Integration (ContextAssembler temporal relations formatting)
10. AST Scope Resolution (CodeAtomDecomposer innermost scope resolution)
"""

from dataclasses import dataclass, field
from datetime import datetime

from apps.api.src.schemas.code_atom import (
    FactConfidence,
    FactType,
    GitCommitArtifact,
    RelationType,
)
from tests.fixtures.atom_eval_dataset import ExpectedFact, ExpectedRelation


@dataclass
class RealRepoCase:
    case_id: str
    name: str
    category: str
    description: str
    commit: GitCommitArtifact
    expected_files: list[str]
    expected_symbols: list[str]
    expected_facts: list[ExpectedFact]
    expected_relations: list[ExpectedRelation]
    retrieval_query: str
    expected_retrieval_targets: list[str]
    rename_history: dict[str, str] = field(default_factory=dict)


def get_real_repo_dataset() -> list[RealRepoCase]:
    cases = []
'''

body = ""
for c in cases_meta:
    sha = c["sha"]
    paths = c["paths"]
    info = (
        subprocess.check_output(["git", "show", "-s", "--format=%an|%ae|%aI|%s", sha], text=True)
        .strip()
        .split("|")
    )
    cmd = ["git", "diff", f"{sha}~1", sha, "--"] + paths
    diff = subprocess.check_output(cmd, text=True)
    if "build.yml" in paths[0]:
        diff = "\n".join(diff.splitlines()[:35])
    diff_escaped = repr(diff)
    dt_str = info[2]
    dt_iso = f"datetime.fromisoformat({repr(dt_str)})"

    symbol_arg = repr(c["expected_symbols"][0]) if c["expected_symbols"] else "None"
    rel_code = f"""[
                ExpectedRelation(
                    subject_keyword={repr(c['rel_subj'])},
                    relation=RelationType.{c['rel_type']},
                    object_keyword={repr(c['rel_obj'])},
                    has_t_start={c['rel_t_start']},
                    has_t_end={c['rel_t_end']},
                )
            ]""" if c["rel_subj"] else "[]"

    body += f"""
    cases.append(
        RealRepoCase(
            case_id={repr(c['case_id'])},
            name={repr(c['description'])},
            category={repr(c['category'])},
            description={repr(c['description'])},
            commit=GitCommitArtifact(
                commit_sha={repr(sha)},
                commit_message={repr(info[3])},
                author_name={repr(info[0])},
                author_email={repr(info[1])},
                committed_at={dt_iso},
                raw_diff={diff_escaped},
            ),
            expected_files={repr(c['expected_files'])},
            expected_symbols={repr(c['expected_symbols'])},
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.{c['fact_type']},
                    confidence=FactConfidence.{c['fact_conf']},
                    is_uncertain={c['fact_unc']},
                    statement_keywords={repr(c['fact_kw'])},
                    symbol_name={symbol_arg},
                )
            ],
            expected_relations={rel_code},
            retrieval_query={repr(c['query'])},
            expected_retrieval_targets={repr(c['targets'])},
            rename_history={repr(c.get('rename_history', {}))},
        )
    )
"""

footer = """
    return cases
"""

with open("tests/fixtures/atom_real_repo_dataset.py", "w", encoding="utf-8") as f:
    f.write(header + body + footer)

print("Successfully written tests/fixtures/atom_real_repo_dataset.py")
