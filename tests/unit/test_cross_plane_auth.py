import asyncio
import os
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.src.auth.security import create_access_token
from apps.api.src.config.settings import settings
from apps.api.src.models.user import User


class TestCrossPlaneAuth(unittest.TestCase):
    def test_jit_user_provisioning_on_data_plane(self):
        async def _run():
            from fastapi.security import HTTPAuthorizationCredentials

            from apps.api.src.api.dependencies.auth import get_current_user

            # Generate token from Control Plane for a user that does not yet exist on Data Plane
            foreign_user_id = uuid.uuid4()
            foreign_email = "architect@acme.com"
            token = create_access_token(
                subject=str(foreign_user_id),
                extra_claims={"email": foreign_email},
            )
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            mock_session = AsyncMock()
            # Initial queries: user by ID returns None, user by email returns None
            empty_result = MagicMock()
            empty_result.scalar_one_or_none.return_value = None

            # Org membership query result
            org_res = MagicMock()
            mock_org_mem = MagicMock()
            mock_org_mem.role = "OWNER"
            org_res.scalar_one_or_none.return_value = mock_org_mem

            mock_session.execute.side_effect = [
                empty_result,  # select by user_id -> None
                empty_result,  # select by email -> None
                org_res,       # org membership check
            ]

            target_org_id = str(uuid.uuid4())
            target_proj_id = str(uuid.uuid4())

            with patch.object(settings, "DATA_PLANE_PROJECT_ID", target_proj_id), patch.object(
                settings, "DATA_PLANE_ORG_ID", target_org_id
            ):
                authenticated_user = await get_current_user(credentials=creds, db=mock_session)

                # Verify JIT user was created with the exact foreign user ID and email
                self.assertEqual(authenticated_user.id, foreign_user_id)
                self.assertEqual(authenticated_user.email, foreign_email)
                # Verify db.add was called to persist user and memberships
                self.assertTrue(mock_session.add.called)
                self.assertTrue(mock_session.commit.called)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
