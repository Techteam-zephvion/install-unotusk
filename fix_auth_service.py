import re

with open('apps/api/src/services/auth_service.py', 'r') as f:
    content = f.read()

helper_method = """

    @staticmethod
    async def _auto_provision_if_needed(session: AsyncSession, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        from apps.api.src.config.settings import settings
        if settings.TARGET_REPO_URL and settings.TARGET_REPO_URL.strip():
            # Check if project already exists
            from apps.api.src.models.project import Project
            from sqlalchemy import select
            
            # Simple check to see if user has any projects
            result = await session.execute(select(Project).where(Project.organization_id == organization_id))
            if result.scalars().first() is not None:
                return # Already provisioned
                
            import urllib.parse
            from apps.api.src.schemas.project import ProjectCreate
            from apps.api.src.schemas.repository import RepositorySelectRequest
            from apps.api.src.services.project_service import ProjectService
            from apps.api.src.services.repository_service import RepositoryService
            from apps.api.src.services.ingestion_service import IngestionService
            
            repo_url = settings.TARGET_REPO_URL.strip()
            path_parts = urllib.parse.urlparse(repo_url).path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[-2]
                name = path_parts[-1]
                if name.endswith(".git"):
                    name = name[:-4]
            else:
                owner, name = "default", "repository"
                
            try:
                project_data = ProjectCreate(
                    name=name,
                    organization_id=organization_id,
                    description=f"Auto-provisioned project for {repo_url}",
                )
                project = await ProjectService.create_project(session, user_id, project_data)
                
                repo_req = RepositorySelectRequest(
                    external_id=f"{owner}_{name}_{uuid.uuid4().hex[:6]}",
                    owner=owner,
                    name=name,
                    full_name=f"{owner}/{name}",
                    url=repo_url,
                )
                repo = await RepositoryService.select_repository(session, user_id, project.id, repo_req)
                await IngestionService.trigger_ingestion(session, user.id, project.id, repo.id)
            except Exception as e:
                import logging
                logger = logging.getLogger("unotusk-api")
                logger.error(f"Failed to auto-provision project from TARGET_REPO_URL: {e}")
"""

# Replace the auto-provisioning block in signup with a call to the helper
old_auto_provision = """        # Auto-provision project and repository if TARGET_REPO_URL is set
        from apps.api.src.config.settings import settings
        if settings.TARGET_REPO_URL and settings.TARGET_REPO_URL.strip():
            import urllib.parse
            from apps.api.src.schemas.project import ProjectCreate
            from apps.api.src.schemas.repository import RepositorySelectRequest
            from apps.api.src.services.project_service import ProjectService
            from apps.api.src.services.repository_service import RepositoryService
            from apps.api.src.services.ingestion_service import IngestionService
            
            repo_url = settings.TARGET_REPO_URL.strip()
            path_parts = urllib.parse.urlparse(repo_url).path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[-2]
                name = path_parts[-1]
                if name.endswith(".git"):
                    name = name[:-4]
            else:
                owner, name = "default", "repository"
                
            try:
                # 1. Create project
                project_data = ProjectCreate(
                    name=name,
                    organization_id=organization.id,
                    description=f"Auto-provisioned project for {repo_url}",
                )
                project = await ProjectService.create_project(session, user.id, project_data)
                
                # 2. Select repository
                repo_req = RepositorySelectRequest(
                    external_id=f"{owner}_{name}_{uuid.uuid4().hex[:6]}",
                    owner=owner,
                    name=name,
                    full_name=f"{owner}/{name}",
                    url=repo_url,
                )
                repo = await RepositoryService.select_repository(session, user.id, project.id, repo_req)
                
                # 3. Trigger ingestion
                await IngestionService.trigger_ingestion(session, user.id, project.id, repo.id)
            except Exception as e:
                import logging
                logger = logging.getLogger("unotusk-api")
                logger.error(f"Failed to auto-provision project from TARGET_REPO_URL: {e}")"""

content = content.replace(old_auto_provision, "        await AuthService._auto_provision_if_needed(session, user.id, organization.id)")

# Also add to existing user signup
existing_user_call = """
            token = create_access_token(
                subject=str(existing_user.id),
                extra_claims={"email": existing_user.email},
            )
            
            await AuthService._auto_provision_if_needed(session, existing_user.id, default_org_id)
            
            return TokenResponse("""
            
content = content.replace("""
            token = create_access_token(
                subject=str(existing_user.id),
                extra_claims={"email": existing_user.email},
            )
            return TokenResponse(""", existing_user_call)

# Add to login
login_call = """
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )
        
        if default_org_id:
            await AuthService._auto_provision_if_needed(session, user.id, default_org_id)
            
        return TokenResponse("""

content = content.replace("""
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )

        return TokenResponse(""", login_call)

# append helper method
content += helper_method

with open('apps/api/src/services/auth_service.py', 'w') as f:
    f.write(content)
