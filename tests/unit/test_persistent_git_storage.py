import asyncio
import os
import tempfile
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.github_client import GitHubClient
from apps.api.src.services.repository_service import RepositoryService


class TestPersistentGitStorage(unittest.TestCase):
    def test_sync_or_clone_repository_when_already_cloned(self):
        client = GitHubClient(token="mock-token")
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock .git directory
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)

            with patch("subprocess.run") as mock_run:
                mock_res = MagicMock()
                mock_res.returncode = 0
                mock_res.stdout = "e4d3c2b1a0"
                mock_run.return_value = mock_res

                sha = client.sync_or_clone_repository(
                    clone_url="https://github.com/acme/proj.git",
                    target_dir=tmpdir,
                    branch="main",
                )
                self.assertEqual(sha, "e4d3c2b1a0")
                calls = [call[0][0] for call in mock_run.call_args_list]
                self.assertTrue(any("fetch" in cmd for cmd in calls))
                self.assertTrue(any("checkout" in cmd for cmd in calls))

    def test_get_file_detail_reads_from_disk_raw_file(self):
        async def _run():
            with tempfile.TemporaryDirectory() as tmpdir:
                repo_name = "test-repo"
                repo_path = os.path.join(tmpdir, repo_name)
                os.makedirs(repo_path, exist_ok=True)

                test_file_rel = "src/main.py"
                test_file_abs = os.path.join(repo_path, test_file_rel)
                os.makedirs(os.path.dirname(test_file_abs), exist_ok=True)
                raw_code = (
                    '"""Module docstring that chunking would lose."""\n'
                    "import os\n"
                    "GLOBAL_CONST = 42\n\n"
                    "def run():\n"
                    "    pass\n"
                )
                with open(test_file_abs, "w") as f:
                    f.write(raw_code)

                mock_project = MagicMock()
                mock_project.id = uuid.uuid4()

                mock_repo = MagicMock(spec=Repository)
                mock_repo.name = repo_name
                mock_repo.full_name = f"org/{repo_name}"
                mock_repo.project_id = mock_project.id

                mock_snap = MagicMock(spec=RepositorySnapshot)
                mock_snap.id = uuid.uuid4()
                mock_snap.commit_sha = "abcdef123"

                mock_file = MagicMock(spec=RepositoryFile)
                mock_file.id = uuid.uuid4()
                mock_file.snapshot_id = mock_snap.id
                mock_file.path = test_file_rel
                mock_file.filename = "main.py"
                mock_file.extension = ".py"
                mock_file.language = "python"
                mock_file.size_bytes = len(raw_code)
                mock_file.content_hash = "mockhash123"
                mock_file.line_count = 6
                mock_file.is_binary = False
                mock_file.is_generated = False
                mock_file.is_test = False

                mock_session = AsyncMock()

                mock_row_result = MagicMock()
                mock_row_result.first.return_value = (mock_file, mock_repo, mock_snap)

                empty_result = MagicMock()
                empty_result.scalars.return_value.all.return_value = []
                empty_result.all.return_value = []

                mock_session.execute.side_effect = [
                    mock_row_result,  # f_query
                    empty_result,     # symbols
                    empty_result,     # out_deps
                    empty_result,     # in_deps
                    empty_result,     # chunks
                ]

                with patch.dict(os.environ, {"UNOTUSK_REPOS_DIR": tmpdir}):
                    with patch.object(
                        RepositoryService,
                        "_verify_project_access",
                        return_value=mock_project,
                    ):
                        file_detail = await RepositoryService.get_file_detail(
                            session=mock_session,
                            user_id=uuid.uuid4(),
                            project_id=mock_project.id,
                            file_id=mock_file.id,
                        )

                        self.assertEqual(file_detail.full_content, raw_code)
                        self.assertIn("Module docstring that chunking would lose", file_detail.full_content)
                        self.assertIn("GLOBAL_CONST = 42", file_detail.full_content)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
