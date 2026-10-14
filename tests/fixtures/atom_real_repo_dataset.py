"""
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

    cases.append(
        RealRepoCase(
            case_id='real_01_method_call',
            name='Method call update in OrchestratorService port extraction',
            category='method_call',
            description='Method call update in OrchestratorService port extraction',
            commit=GitCommitArtifact(
                commit_sha='4e5af911a97f098ac816c93a23caeb562ca007fb',
                commit_message='fix(lint): use port_bindings.values() to resolve ruff B007 unused variable',
                author_name='dhanush',
                author_email='dhanushk2204@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T14:08:51+05:30'),
                raw_diff='diff --git a/apps/api/src/services/orchestrator_service.py b/apps/api/src/services/orchestrator_service.py\nindex 5c1e446..d7b824a 100644\n--- a/apps/api/src/services/orchestrator_service.py\n+++ b/apps/api/src/services/orchestrator_service.py\n@@ -97,7 +97,7 @@ class OrchestratorService:\n             container = client.containers.get(container_name)\n             port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})\n             assigned_port = None\n-            for port_key, bindings in port_bindings.items():\n+            for bindings in port_bindings.values():\n                 if bindings:\n                     assigned_port = int(bindings[0].get("HostPort"))\n                     break\n',
            ),
            expected_files=['apps/api/src/services/orchestrator_service.py'],
            expected_symbols=['OrchestratorService'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.UNCERTAIN,
                    is_uncertain=True,
                    statement_keywords=['port_bindings', 'values'],
                    symbol_name='OrchestratorService',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='OrchestratorService',
                    relation=RelationType.CALLS,
                    object_keyword='port_bindings',
                    has_t_start=True,
                    has_t_end=True,
                )
            ],
            retrieval_query='How are host port bindings extracted in OrchestratorService?',
            expected_retrieval_targets=['apps/api/src/services/orchestrator_service.py', 'OrchestratorService'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_02_removal',
            name='Dead code removal of new_memberships_added in ProjectService',
            category='removal',
            description='Dead code removal of new_memberships_added in ProjectService',
            commit=GitCommitArtifact(
                commit_sha='24a2630c9e8d213fa85a98624630da9c9c15159d',
                commit_message='fix(lint): remove unused new_memberships_added variable in project_service.py',
                author_name='BenakaPrasad',
                author_email='benakaprasadm@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T17:09:00+05:30'),
                raw_diff='diff --git a/apps/api/src/services/project_service.py b/apps/api/src/services/project_service.py\nindex b0ca278..23ec675 100644\n--- a/apps/api/src/services/project_service.py\n+++ b/apps/api/src/services/project_service.py\n@@ -456,7 +456,6 @@ class ProjectService:\n         )\n         existing_pm_user_ids = set((await session.execute(existing_pms_query)).scalars().all())\n \n-        new_memberships_added = False\n         for u in all_users:\n             if u.id not in existing_pm_user_ids:\n                 is_u_admin = u.email.lower() == "admin@acme.com"\n@@ -476,7 +475,6 @@ class ProjectService:\n                     user_id=u.id,\n                     role=u_role,\n                 ))\n-                new_memberships_added = True\n \n         await session.commit()\n \n',
            ),
            expected_files=['apps/api/src/services/project_service.py'],
            expected_symbols=['ProjectService'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.REMOVAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=['new_memberships_added'],
                    symbol_name='ProjectService',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='ProjectService',
                    relation=RelationType.REFERENCES,
                    object_keyword='logic',
                    has_t_start=False,
                    has_t_end=True,
                )
            ],
            retrieval_query='Where was unused new_memberships_added removed from project member synchronization?',
            expected_retrieval_targets=['apps/api/src/services/project_service.py', 'ProjectService'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_03_method_replacement',
            name='Replaced deprecated Matrix4.scale with scaleByDouble in Mermaid diagram',
            category='method_replacement',
            description='Replaced deprecated Matrix4.scale with scaleByDouble in Mermaid diagram',
            commit=GitCommitArtifact(
                commit_sha='a9d81bbb74279e12121243f44cd11dfdaf28a794',
                commit_message='fix(analyzer): replace deprecated Matrix4.scale with scaleByDouble in mermaid diagram',
                author_name='BenakaPrasad',
                author_email='benakaprasadm@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T17:05:23+05:30'),
                raw_diff='diff --git a/app/lib/widgets/mermaid_diagram.dart b/app/lib/widgets/mermaid_diagram.dart\nindex 8391303..d1b2330 100644\n--- a/app/lib/widgets/mermaid_diagram.dart\n+++ b/app/lib/widgets/mermaid_diagram.dart\n@@ -586,13 +586,13 @@ class _MermaidFullscreenDialogState extends State<_MermaidFullscreenDialog> {\n \n   void _zoomIn() {\n     final matrix = _transController.value.clone();\n-    matrix.scale(1.3, 1.3);\n+    matrix.scaleByDouble(1.3, 1.3, 1.0, 1.0);\n     _transController.value = matrix;\n   }\n \n   void _zoomOut() {\n     final matrix = _transController.value.clone();\n-    matrix.scale(0.77, 0.77);\n+    matrix.scaleByDouble(0.77, 0.77, 1.0, 1.0);\n     _transController.value = matrix;\n   }\n \n',
            ),
            expected_files=['app/lib/widgets/mermaid_diagram.dart'],
            expected_symbols=['_MermaidFullscreenDialogState'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.UNCERTAIN,
                    is_uncertain=True,
                    statement_keywords=['scalebydouble'],
                    symbol_name='_MermaidFullscreenDialogState',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='_MermaidFullscreenDialogState',
                    relation=RelationType.CALLS,
                    object_keyword='matrix',
                    has_t_start=True,
                    has_t_end=True,
                )
            ],
            retrieval_query='How is matrix scaling implemented in the mermaid diagram fullscreen dialog?',
            expected_retrieval_targets=['app/lib/widgets/mermaid_diagram.dart', '_MermaidFullscreenDialogState'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_04_imports_refactor',
            name='Added func import to sqlalchemy in auth_service for query optimization',
            category='imports_refactor',
            description='Added func import to sqlalchemy in auth_service for query optimization',
            commit=GitCommitArtifact(
                commit_sha='356d19b536c9cc9e147392c59427a3936b135a17',
                commit_message='fix(lint): resolve ruff undefined func, unused datetime, and import sorting',
                author_name='BenakaPrasad',
                author_email='benakaprasadm@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T17:02:59+05:30'),
                raw_diff='diff --git a/apps/api/src/services/auth_service.py b/apps/api/src/services/auth_service.py\nindex 258dc77..14c73cd 100644\n--- a/apps/api/src/services/auth_service.py\n+++ b/apps/api/src/services/auth_service.py\n@@ -1,6 +1,6 @@\n import uuid\n \n-from sqlalchemy import select\n+from sqlalchemy import func, select\n from sqlalchemy.ext.asyncio import AsyncSession\n \n from apps.api.src.api.exceptions import (\n',
            ),
            expected_files=['apps/api/src/services/auth_service.py'],
            expected_symbols=[],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=['sqlalchemy'],
                    symbol_name=None,
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='auth_service',
                    relation=RelationType.IMPORTS,
                    object_keyword='sqlalchemy',
                    has_t_start=True,
                    has_t_end=True,
                )
            ],
            retrieval_query='Which module imports sqlalchemy func for case-insensitive email queries in auth?',
            expected_retrieval_targets=['apps/api/src/services/auth_service.py'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_05_configuration',
            name='Platform environment and web guard check in ApiService',
            category='configuration',
            description='Platform environment and web guard check in ApiService',
            commit=GitCommitArtifact(
                commit_sha='5526ed5578676fa515ec9a88f41844454278449f',
                commit_message='fix(docker,web): align API_PORT in .env to 28000, rebuild images, and add web platform guards for Flutter',
                author_name='dhanush',
                author_email='dhanushk2204@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T13:42:38+05:30'),
                raw_diff="diff --git a/app/lib/services/api_service.dart b/app/lib/services/api_service.dart\nindex 5bfeb80..1d55625 100644\n--- a/app/lib/services/api_service.dart\n+++ b/app/lib/services/api_service.dart\n@@ -402,7 +402,7 @@ class ApiService {\n \n   /// Fetches project list from http://10.0.0.59:28000/api/v1/projects\n   static Future<List<ProjectItem>> fetchProjects() async {\n-    if (Platform.environment.containsKey('FLUTTER_TEST')) {\n+    if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {\n       final mock = [\n         const ProjectItem(\n           id: 'proj-1',\n",
            ),
            expected_files=['app/lib/services/api_service.dart'],
            expected_symbols=['ApiService'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.UNCERTAIN,
                    is_uncertain=True,
                    statement_keywords=['environment'],
                    symbol_name='ApiService',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='ApiService',
                    relation=RelationType.CALLS,
                    object_keyword='environment',
                    has_t_start=True,
                    has_t_end=True,
                )
            ],
            retrieval_query='What is the configured port or test environment check in ApiService?',
            expected_retrieval_targets=['app/lib/services/api_service.dart', 'ApiService'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_06_admin_guard',
            name='Permanent lead admin assignment in AuthService for admin@acme.com',
            category='admin_guard',
            description='Permanent lead admin assignment in AuthService for admin@acme.com',
            commit=GitCommitArtifact(
                commit_sha='808b4021451d50c4dead63db45fc606f078608a9',
                commit_message='fix(workspace): establish permanent lead admin status with full repository access',
                author_name='BenakaPrasad',
                author_email='benakaprasadm@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T16:12:07+05:30'),
                raw_diff='diff --git a/apps/api/src/services/auth_service.py b/apps/api/src/services/auth_service.py\nindex a70955c..789f8bb 100644\n--- a/apps/api/src/services/auth_service.py\n+++ b/apps/api/src/services/auth_service.py\n@@ -62,7 +62,10 @@ class AuthService:\n             session.add(existing_user)\n \n             role_raw = (data.role or "").strip().lower()\n-            assigned_role = MembershipRole.ADMIN if ("manager" in role_raw or "admin" in role_raw or "lead" in role_raw) else MembershipRole.MEMBER\n+            if normalized_email == "admin@acme.com":\n+                assigned_role = MembershipRole.ADMIN\n+            else:\n+                assigned_role = MembershipRole.ADMIN if ("manager" in role_raw or "admin" in role_raw or "lead" in role_raw) else MembershipRole.MEMBER\n \n             # Check if user has an org membership\n             org_mem_query = await session.execute(\n@@ -128,7 +131,9 @@ class AuthService:\n \n         # Determine desired role from data.role (maps Manager -> ADMIN, Member(Dev) -> MEMBER)\n         role_raw = (data.role or "").strip().lower()\n-        if "manager" in role_raw or "admin" in role_raw or "lead" in role_raw:\n+        if normalized_email == "admin@acme.com":\n+            assigned_role = MembershipRole.ADMIN\n+        elif "manager" in role_raw or "admin" in role_raw or "lead" in role_raw:\n             assigned_role = MembershipRole.ADMIN\n         else:\n             assigned_role = MembershipRole.MEMBER\n',
            ),
            expected_files=['apps/api/src/services/auth_service.py'],
            expected_symbols=['AuthService'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.UNCERTAIN,
                    is_uncertain=True,
                    statement_keywords=['admin@acme.com'],
                    symbol_name='AuthService',
                )
            ],
            expected_relations=[],
            retrieval_query='How does AuthService assign the ADMIN role permanently to admin@acme.com?',
            expected_retrieval_targets=['apps/api/src/services/auth_service.py', 'AuthService'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_07_rbac_isolation',
            name='Enforce organization isolation and ConflictException when adding project members',
            category='rbac_isolation',
            description='Enforce organization isolation and ConflictException when adding project members',
            commit=GitCommitArtifact(
                commit_sha='cbbbbae8731ceb7e8532f58d71bff757ea3789bb',
                commit_message='fix(rbac): resolve User.is_active schema mismatch, Matrix4 scale deprecation, and org isolation in member sync',
                author_name='Techteam-zephvion',
                author_email='techteam.zephvion@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-13T17:14:53+05:30'),
                raw_diff='diff --git a/apps/api/src/services/project_service.py b/apps/api/src/services/project_service.py\nindex 28423cc..9b484b4 100644\n--- a/apps/api/src/services/project_service.py\n+++ b/apps/api/src/services/project_service.py\n@@ -1,4 +1,3 @@\n-from datetime import datetime\n import logging\n import uuid\n \n@@ -6,12 +5,12 @@ from sqlalchemy import func, select\n from sqlalchemy.ext.asyncio import AsyncSession\n from sqlalchemy.orm import selectinload\n \n-from apps.api.src.auth.security import hash_password\n from apps.api.src.api.exceptions import (\n     ConflictException,\n     ForbiddenException,\n     NotFoundException,\n )\n+from apps.api.src.auth.security import hash_password\n from apps.api.src.models.enums import (\n     IntegrationProvider,\n     IntegrationStatus,\n@@ -20,6 +19,7 @@ from apps.api.src.models.enums import (\n )\n from apps.api.src.models.integration import Integration\n from apps.api.src.models.membership import OrganizationMembership, ProjectMembership\n+from apps.api.src.models.organization import Organization\n from apps.api.src.models.project import Project\n from apps.api.src.models.repository import Repository\n from apps.api.src.models.user import User\n@@ -573,56 +573,66 @@ class ProjectService:\n                 message="Project not found",\n             )\n \n-        # Ensure permanent admin@acme.com exists and is always linked with OWNER/ADMIN privileges\n-        admin_user_res = await session.execute(\n-            select(User).where(func.lower(User.email) == "admin@acme.com")\n+        # Caller info\n+        caller = await session.get(User, user_id)\n+        is_lead_admin = caller is not None and caller.email.lower() == "admin@acme.com"\n+\n+        # Check if project belongs to Acme Corporation or if caller is Lead Admin\n+        org_query = select(Organization).where(Organization.id == project.organization_id)\n+        project_org = (await session.execute(org_query)).scalar_one_or_none()\n+        is_acme_org = (\n+            (project_org is not None and "acme" in project_org.slug.lower())\n+            or is_lead_admin\n         )\n-        admin_user = admin_user_res.scalar_one_or_none()\n-        if admin_user is None:\n-            admin_user = User(\n-                email="admin@acme.com",\n-                name="Lead Admin",\n-                password_hash=hash_password("admin123"),\n-                is_active=True,\n-            )\n-            session.add(admin_user)\n-            await session.flush()\n \n-        admin_om_res = await session.execute(\n-            select(OrganizationMembership).where(\n-                OrganizationMembership.organization_id == project.organization_id,\n-                OrganizationMembership.user_id == admin_user.id,\n+        if is_acme_org:\n+            # Ensure permanent admin@acme.com exists and is always linked with OWNER/ADMIN privileges\n+            admin_user_res = await session.execute(\n+                select(User).where(func.lower(User.email) == "admin@acme.com")\n+            )\n+            admin_user = admin_user_res.scalar_one_or_none()\n+            if admin_user is None:\n+                admin_user = User(\n+                    email="admin@acme.com",\n+                    name="Lead Admin",\n+                    password_hash=hash_password("admin123"),\n+                )\n+                session.add(admin_user)\n+                await session.flush()\n+\n+            admin_om_res = await session.execute(\n+                select(OrganizationMembership).where(\n+                    OrganizationMembership.organization_id == project.organization_id,\n+                    OrganizationMembership.user_id == admin_user.id,\n+                )\n             )\n-        )\n-        admin_om = admin_om_res.scalar_one_or_none()\n-        if admin_om is None:\n-            session.add(OrganizationMembership(\n-                organization_id=project.organization_id,\n-                user_id=admin_user.id,\n-                role=MembershipRole.OWNER,\n-            ))\n-        elif admin_om.role != MembershipRole.OWNER:\n-            admin_om.role = MembershipRole.OWNER\n-\n-        admin_pm_res = await session.execute(\n-            select(ProjectMembership).where(\n-                ProjectMembership.project_id == resolved_id,\n-                ProjectMembership.user_id == admin_user.id,\n+            admin_om = admin_om_res.scalar_one_or_none()\n+            if admin_om is None:\n+                session.add(OrganizationMembership(\n+                    organization_id=project.organization_id,\n+                    user_id=admin_user.id,\n+                    role=MembershipRole.OWNER,\n+                ))\n+            elif admin_om.role != MembershipRole.OWNER:\n+                admin_om.role = MembershipRole.OWNER\n+\n+            admin_pm_res = await session.execute(\n+                select(ProjectMembership).where(\n+                    ProjectMembership.project_id == resolved_id,\n+                    ProjectMembership.user_id == admin_user.id,\n+                )\n             )\n-        )\n-        admin_pm = admin_pm_res.scalar_one_or_none()\n-        if admin_pm is None:\n-            session.add(ProjectMembership(\n-                project_id=resolved_id,\n-                user_id=admin_user.id,\n-                role=MembershipRole.ADMIN,\n-            ))\n-        elif admin_pm.role != MembershipRole.ADMIN:\n-            admin_pm.role = MembershipRole.ADMIN\n+            admin_pm = admin_pm_res.scalar_one_or_none()\n+            if admin_pm is None:\n+                session.add(ProjectMembership(\n+                    project_id=resolved_id,\n+                    user_id=admin_user.id,\n+                    role=MembershipRole.ADMIN,\n+                ))\n+            elif admin_pm.role != MembershipRole.ADMIN:\n+                admin_pm.role = MembershipRole.ADMIN\n \n-        # Check caller permissions - Lead Admin admin@acme.com always has unrestricted access\n-        caller = await session.get(User, user_id)\n-        is_lead_admin = caller is not None and caller.email.lower() == "admin@acme.com"\n+            await session.flush()\n \n         if not is_lead_admin:\n             mem_query = select(OrganizationMembership).where(\n@@ -651,24 +661,28 @@ class ProjectService:\n                         message="You do not have access to this project",\n                     )\n \n-        # In single-tenant MVP, ensure all registered users are synchronized into ProjectMembership\n-        # for this project so the Lead Admin can immediately see, search, and manage all workspace employees.\n-        all_users_query = select(User).where(User.is_active == True)\n-        all_users_res = await session.execute(all_users_query)\n-        all_users = all_users_res.scalars().all()\n+        # In single-tenant MVP, ensure organization users are synchronized into ProjectMembership\n+        # for this project so the Lead Admin can immediately see, search, and manage workspace employees.\n+        org_users_query = (\n+            select(User)\n+            .join(OrganizationMembership, OrganizationMembership.user_id == User.id)\n+            .where(OrganizationMembership.organization_id == project.organization_id)\n+        )\n+        org_users_res = await session.execute(org_users_query)\n+        org_users = org_users_res.scalars().all()\n \n         existing_pms_query = select(ProjectMembership.user_id).where(\n             ProjectMembership.project_id == resolved_id\n         )\n         existing_pm_user_ids = set((await session.execute(existing_pms_query)).scalars().all())\n \n-        new_memberships_added = False\n-        for u in all_users:\n+        for u in org_users:\n             if u.id not in existing_pm_user_ids:\n                 is_u_admin = u.email.lower() == "admin@acme.com"\n                 om_res = await session.execute(\n                     select(OrganizationMembership.role).where(\n-                        OrganizationMembership.user_id == u.id\n+                        OrganizationMembership.user_id == u.id,\n+                        OrganizationMembership.organization_id == project.organization_id,\n                     ).limit(1)\n                 )\n                 om_role = om_res.scalar_one_or_none()\n@@ -682,7 +696,7 @@ class ProjectService:\n                     user_id=u.id,\n                     role=u_role,\n                 ))\n-                new_memberships_added = True\n+                existing_pm_user_ids.add(u.id)\n \n         await session.commit()\n \n@@ -812,18 +826,6 @@ class ProjectService:\n                 )\n                 target_user = u_res.scalar_one_or_none()\n \n-            # 4. Auto-provision employee if not yet registered in single-tenant MVP\n-            if target_user is None:\n-                email_val = clean_identifier if "@" in clean_identifier else f"{clean_identifier.replace(\' \', \'.\')}@acme.com"\n-                name_val = clean_identifier if "@" not in clean_identifier else clean_identifier.split("@")[0].title()\n-                target_user = User(\n-                    email=email_val,\n-                    name=name_val,\n-                    password_hash=hash_password("password123"),\n-                )\n-                session.add(target_user)\n-                await session.flush()\n-\n         if target_user is None:\n             raise NotFoundException(\n                 code="USER_NOT_FOUND",\n@@ -836,7 +838,7 @@ class ProjectService:\n                 message="admin@acme.com is the permanent Lead Administrator with full repository access and cannot be re-assigned or demoted.",\n             )\n \n-        # Target user must be part of the organization - auto-assign if missing in single-tenant setup\n+        # Target user must be part of the organization\n         target_org_mem_res = await session.execute(\n             select(OrganizationMembership).where(\n                 OrganizationMembership.organization_id == project.organization_id,\n@@ -845,13 +847,10 @@ class ProjectService:\n         )\n         target_org_mem = target_org_mem_res.scalar_one_or_none()\n         if target_org_mem is None:\n-            target_org_mem = OrganizationMembership(\n-                organization_id=project.organization_id,\n-                user_id=target_user.id,\n-                role=data.role,\n+            raise ConflictException(\n+                code="USER_NOT_IN_ORGANIZATION",\n+                message="User is not a member of the organization",\n             )\n-            session.add(target_org_mem)\n-            await session.flush()\n \n         # Check if already a project member - update role if existing, else add new\n         existing_pm = await session.execute(\n@@ -862,6 +861,11 @@ class ProjectService:\n         )\n         pm = existing_pm.scalar_one_or_none()\n         if pm is not None:\n+            if pm.role == data.role or data.user_id is not None:\n+                raise ConflictException(\n+                    code="MEMBER_ALREADY_EXISTS",\n+                    message="User is already a member of this project",\n+                )\n             pm.role = data.role\n             new_membership = pm\n         else:\n',
            ),
            expected_files=['apps/api/src/services/project_service.py'],
            expected_symbols=['ProjectService'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.ERROR_HANDLING,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=['conflictexception'],
                    symbol_name='ProjectService',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='ProjectService',
                    relation=RelationType.RAISES,
                    object_keyword='ConflictException',
                    has_t_start=True,
                    has_t_end=False,
                )
            ],
            retrieval_query='Where does ProjectService validate organization membership before adding a member to a project?',
            expected_retrieval_targets=['apps/api/src/services/project_service.py', 'ProjectService'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_08_file_rename',
            name='Workflow rename from build.yml to release.yml',
            category='file_rename',
            description='Workflow rename from build.yml to release.yml',
            commit=GitCommitArtifact(
                commit_sha='6f7570fc92a9fcf0645ee94b86d3d861c3b161e5',
                commit_message='feat(release): decouple workflows, support Hindu release codenames, and auto-sync install portal',
                author_name='Techteam-zephvion',
                author_email='techteam.zephvion@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-04T12:37:02+05:30'),
                raw_diff='diff --git a/.github/workflows/build.yml b/.github/workflows/release.yml\nsimilarity index 57%\nrename from .github/workflows/build.yml\nrename to .github/workflows/release.yml\nindex a068dc6..6b5be0e 100644\n--- a/.github/workflows/build.yml\n+++ b/.github/workflows/release.yml\n@@ -1,37 +1,36 @@\n-name: Build Employee App â€” All Platforms\n+name: Release â€” Build Multi-Platform Installers & Sync Portal\n \n on:\n   push:\n-    branches: [main, master]\n     tags:\n-      - "v*"\n+      - "*"\n   workflow_dispatch:\n     inputs:\n-      version:\n-        description: "Version tag (e.g. 1.0.0)"\n-        required: false\n-        default: "dev"\n+      tag:\n+        description: "Release Tag / Codename (e.g. v1.0.1-rudra, aditya, v1.0.1-dhruv)"\n+        required: true\n+        default: "v1.0.1-rudra"\n \n concurrency:\n   group: ${{ github.workflow }}-${{ github.ref }}\n-  cancel-in-progress: true\n+  cancel-in-progress: false\n \n env:\n   FLUTTER_VERSION: "3.x"',
            ),
            expected_files=['.github/workflows/release.yml'],
            expected_symbols=[],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.STRUCTURAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=['release.yml', 'build.yml'],
                    symbol_name=None,
                )
            ],
            expected_relations=[],
            retrieval_query='Which GitHub workflow file handles release builds after decoupling from build.yml?',
            expected_retrieval_targets=['.github/workflows/release.yml'],
            rename_history={'.github/workflows/build.yml': '.github/workflows/release.yml'},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_09_pipeline_integration',
            name='ContextAssembler formatting of temporal relations with ended tag',
            category='pipeline_integration',
            description='ContextAssembler formatting of temporal relations with ended tag',
            commit=GitCommitArtifact(
                commit_sha='b094f015541718f5cec08f092f004a0fc6c3aa63',
                commit_message='Integrated temporal code relation pipeline',
                author_name='Savan G',
                author_email='savan.guntakal@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-14T12:08:33+05:30'),
                raw_diff='diff --git a/apps/api/src/services/context_engine/assembler.py b/apps/api/src/services/context_engine/assembler.py\nindex 9b495df..bc40295 100644\n--- a/apps/api/src/services/context_engine/assembler.py\n+++ b/apps/api/src/services/context_engine/assembler.py\n@@ -134,7 +134,8 @@ class ContextAssembler:\n                         time_str = f" [t_start: {t_s or \'None\'}, t_end: {t_e or \'None\'}]"\n                         conflict_tag = " (conflict)" if rel.get("has_temporal_conflict") else ""\n                         uncertain_tag = " (uncertain)" if rel.get("is_uncertain") and not conflict_tag else ""\n-                        rel_lines.append(f"  * ({subj}, {r_type}, {obj}){time_str}{conflict_tag}{uncertain_tag}")\n+                        ended_tag = " (ended)" if t_e else ""\n+                        rel_lines.append(f"  * ({subj}, {r_type}, {obj}){time_str}{conflict_tag}{uncertain_tag}{ended_tag}")\n                     elif isinstance(rel, str):\n                         rel_lines.append(f"  * {rel}")\n                 if rel_lines:\n',
            ),
            expected_files=['apps/api/src/services/context_engine/assembler.py'],
            expected_symbols=['ContextAssembler'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.RELATIONSHIP,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=['rel_lines', 'append'],
                    symbol_name='ContextAssembler',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='ContextAssembler',
                    relation=RelationType.CALLS,
                    object_keyword='rel_lines',
                    has_t_start=True,
                    has_t_end=True,
                )
            ],
            retrieval_query='How does ContextAssembler format temporal relationships and conflict warnings in prompt context?',
            expected_retrieval_targets=['apps/api/src/services/context_engine/assembler.py', 'ContextAssembler'],
            rename_history={},
        )
    )

    cases.append(
        RealRepoCase(
            case_id='real_10_scope_resolution',
            name='CodeAtomDecomposer AST line bound resolution with innermost scope preference',
            category='scope_resolution',
            description='CodeAtomDecomposer AST line bound resolution with innermost scope preference',
            commit=GitCommitArtifact(
                commit_sha='be1b5b5c2a96fdef91b571e3d32f9f587c4d4ed8',
                commit_message='Enhanced Code Lane AST scope resolution and provenance fidelity',
                author_name='Savan G',
                author_email='savan.guntakal@gmail.com',
                committed_at=datetime.fromisoformat('2026-10-14T14:05:51+05:30'),
                raw_diff='diff --git a/apps/api/src/services/code_atom/decomposer.py b/apps/api/src/services/code_atom/decomposer.py\nindex 9940246..aa54526 100644\n--- a/apps/api/src/services/code_atom/decomposer.py\n+++ b/apps/api/src/services/code_atom/decomposer.py\n@@ -97,12 +97,22 @@ class CodeAtomDecomposer:\n \n             for hunk in file_diff.hunks:\n                 # Correlate symbol from symbol catalog or hunk section header\n+                new_start = hunk.new_start_line\n+                new_end = (\n+                    hunk.new_start_line + hunk.new_line_count - 1\n+                    if hunk.new_line_count > 0\n+                    else hunk.new_start_line\n+                )\n                 symbol_id, symbol_name, symbol_type = self._resolve_symbol(\n                     file_path=file_diff.new_path,\n-                    start_line=hunk.new_start_line,\n-                    end_line=hunk.new_start_line + hunk.new_line_count - 1,\n+                    start_line=new_start,\n+                    end_line=new_end,\n                     section_header=hunk.section_header,\n                     symbol_catalog=symbol_catalog,\n+                    old_file_path=file_diff.old_path,\n+                    old_start_line=hunk.old_start_line,\n+                    old_line_count=hunk.old_line_count,\n+                    new_line_count=hunk.new_line_count,\n                 )\n \n                 if symbol_name:\n@@ -286,33 +296,116 @@ class CodeAtomDecomposer:\n         file_path: str,\n         start_line: int,\n         end_line: int,\n-        section_header: str | None,\n-        symbol_catalog: list[dict[str, Any]] | None,\n+        section_header: str | None = None,\n+        symbol_catalog: list[dict[str, Any]] | None = None,\n+        old_file_path: str | None = None,\n+        old_start_line: int | None = None,\n+        old_line_count: int | None = None,\n+        new_line_count: int | None = None,\n     ) -> tuple[uuid.UUID | None, str | None, str | None]:\n-        """Resolves symbol identity from catalog or falls back to hunk header hint."""\n-        clean_file = file_path.replace("\\\\", "/").strip().lower()\n+        """\n+        Resolves symbol identity from AST catalog or falls back to hunk header hint.\n+\n+        Guarantees:\n+        1. Innermost enclosing symbol preference: when nested symbols enclose the line range\n+           (e.g., method within class), selects the most specific (innermost) symbol.\n+        2. Deletion handling: when new_line_count == 0 (pure deletion), correlates against\n+           old_start_line and old_line_count in symbol catalog.\n+        3. File path normalization & rename handling: matches against normalized new or old file path.\n+        4. Hunk header symbol alignment: if diff header specifies symbol name but lines shifted,\n+           matches named symbol from symbol catalog to preserve AST UUID.\n+        5. Safe file-level fallback: returns (None, None, None) without hallucinating scope\n+           when no enclosing symbol exists (e.g., top-level assignments or imports).\n+        """\n+        clean_new = file_path.replace("\\\\", "/").strip().lower().lstrip("/")\n+        clean_old = (\n+            old_file_path.replace("\\\\", "/").strip().lower().lstrip("/")\n+            if old_file_path\n+            else None\n+        )\n \n-        # 1. Try matching with provided AST symbol catalog\n+        # 1. Determine effective query line range\n+        is_deletion = (new_line_count == 0) or (start_line > end_line)\n+        if not is_deletion and start_line > 0 and end_line >= start_line:\n+            q_start, q_end = start_line, end_line\n+        elif (\n+            old_start_line is not None\n+            and old_line_count is not None\n+            and old_start_line > 0\n+            and old_line_count > 0\n+        ):\n+            q_start = old_start_line\n+            q_end = old_start_line + old_line_count - 1\n+        elif start_line > 0:\n+            q_start, q_end = start_line, max(start_line, end_line)\n+        else:\n+            q_start, q_end = 0, 0\n+\n+        # 2. Filter symbol catalog for matching candidate symbols in this file\n+        candidate_symbols: list[dict[str, Any]] = []\n         if symbol_catalog:\n             for sym in symbol_catalog:\n-                sym_path = str(sym.get("file_path", "")).replace("\\\\", "/").strip().lower()\n-                if sym_path and sym_path != clean_file:\n+                sym_path = str(sym.get("file_path", "")).replace("\\\\", "/").strip().lower().lstrip("/")\n+                if not sym_path:\n+                    candidate_symbols.append(sym)\n                     continue\n \n-                sym_start = sym.get("start_line", 0)\n-                sym_end = sym.get("end_line", 0)\n-                # Check line range overlap\n-                if max(start_line, sym_start) <= min(end_line, sym_end):\n-                    raw_id = sym.get("id")\n-                    sym_uuid = uuid.UUID(str(raw_id)) if raw_id else None\n-                    return sym_uuid, sym.get("name"), sym.get("symbol_type")\n+                if sym_path == clean_new or (clean_old and sym_path == clean_old):\n+                    candidate_symbols.append(sym)\n+                elif sym_path.endswith(f"/{clean_new}") or clean_new.endswith(f"/{sym_path}"):\n+                    candidate_symbols.append(sym)\n+                elif clean_old and (sym_path.endswith(f"/{clean_old}") or clean_old.endswith(f"/{sym_path}")):\n+                    candidate_symbols.append(sym)\n+\n+        # 3. Correlate with AST symbol line bounds\n+        if candidate_symbols and q_start > 0:\n+            containing_symbols: list[tuple[int, dict[str, Any]]] = []\n+            overlapping_symbols: list[tuple[int, int, dict[str, Any]]] = []\n+\n+            for sym in candidate_symbols:\n+                s_start = sym.get("start_line", 0)\n+                s_end = sym.get("end_line", 0)\n+                if s_start <= 0 or s_end <= 0:\n+                    continue\n \n-        # 2. Fall back to parsing the diff hunk section header\n+                span = max(1, s_end - s_start + 1)\n+                if s_start <= q_start and q_end <= s_end:\n+                    containing_symbols.append((span, sym))\n+                else:\n+                    overlap = max(0, min(q_end, s_end) - max(q_start, s_start) + 1)\n+                    if overlap > 0:\n+                        overlapping_symbols.append((overlap, span, sym))\n+\n+            if containing_symbols:\n+                containing_symbols.sort(key=lambda x: x[0])  # Smallest span = innermost symbol\n+                best_sym = containing_symbols[0][1]\n+                raw_id = best_sym.get("id")\n+                sym_uuid = uuid.UUID(str(raw_id)) if raw_id else None\n+                return sym_uuid, best_sym.get("name"), best_sym.get("symbol_type")\n+\n+            if overlapping_symbols:\n+                overlapping_symbols.sort(key=lambda x: (-x[0], x[1]))  # Highest overlap, then smallest span\n+                best_sym = overlapping_symbols[0][2]\n+                raw_id = best_sym.get("id")\n+                sym_uuid = uuid.UUID(str(raw_id)) if raw_id else None\n+                return sym_uuid, best_sym.get("name"), best_sym.get("symbol_type")\n+\n+        # 4. Fall back to parsing the diff hunk section header\n+        header_symbol_name: str | None = None\n         if section_header:\n             match = SYMBOL_HEADER_PATTERN.search(section_header)\n             if match:\n-                return None, match.group(1), "FUNCTION_OR_CLASS"\n+                header_symbol_name = match.group(1)\n+\n+        if header_symbol_name:\n+            for sym in candidate_symbols:\n+                if sym.get("name") == header_symbol_name:\n+                    raw_id = sym.get("id")\n+                    sym_uuid = uuid.UUID(str(raw_id)) if raw_id else None\n+                    return sym_uuid, sym.get("name"), sym.get("symbol_type") or "FUNCTION_OR_CLASS"\n+            return None, header_symbol_name, "FUNCTION_OR_CLASS"\n \n+        # 5. Safe file-level fallback\n         return None, None, None\n \n     def _create_file_level_atomic_change(\n',
            ),
            expected_files=['apps/api/src/services/code_atom/decomposer.py'],
            expected_symbols=['CodeAtomDecomposer'],
            expected_facts=[
                ExpectedFact(
                    fact_type=FactType.STRUCTURAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    statement_keywords=['candidate_symbols'],
                    symbol_name='CodeAtomDecomposer',
                )
            ],
            expected_relations=[
                ExpectedRelation(
                    subject_keyword='CodeAtomDecomposer',
                    relation=RelationType.CALLS,
                    object_keyword='candidate_symbols',
                    has_t_start=True,
                    has_t_end=False,
                )
            ],
            retrieval_query='Where is AST symbol catalog correlation and innermost scope resolution implemented for diff hunks?',
            expected_retrieval_targets=['apps/api/src/services/code_atom/decomposer.py', 'CodeAtomDecomposer'],
            rename_history={},
        )
    )

    return cases
