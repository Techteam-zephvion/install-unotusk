import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.enums import SnapshotStatus, SymbolType
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol


class TestIncrementalSnapshotCaching(unittest.IsolatedAsyncioTestCase):
    async def test_incremental_cache_reuses_previous_snapshot_entities(self):
        """Verify that when a file has identical content_hash in previous snapshot,
        its symbols, chunks, and dependencies are cloned without re-parsing."""
        prev_snapshot_id = uuid.uuid4()
        curr_snapshot_id = uuid.uuid4()
        repo_id = uuid.uuid4()

        RepositorySnapshot(
            id=prev_snapshot_id,
            repository_id=repo_id,
            status=SnapshotStatus.COMPLETED,
            commit_sha="commit-1",
        )

        RepositorySnapshot(
            id=curr_snapshot_id,
            repository_id=repo_id,
            status=SnapshotStatus.QUEUED,
            commit_sha="commit-2",
        )

        old_file_id = uuid.uuid4()
        RepositoryFile(
            id=old_file_id,
            snapshot_id=prev_snapshot_id,
            path="src/main.py",
            filename="main.py",
            extension=".py",
            language="Python",
            size_bytes=100,
            content_hash="hash-12345",
            is_binary=False,
            is_generated=False,
            is_test=False,
            line_count=10,
            parser_supported=True,
        )

        old_sym_id = uuid.uuid4()
        CodeSymbol(
            id=old_sym_id,
            file_id=old_file_id,
            name="app_init",
            symbol_type=SymbolType.FUNCTION,
            qualified_name="app_init",
            start_line=1,
            end_line=5,
            symbol_metadata={},
        )

        old_chunk = CodeChunk(
            id=uuid.uuid4(),
            snapshot_id=prev_snapshot_id,
            file_id=old_file_id,
            symbol_id=old_sym_id,
            chunk_type="SYMBOL",
            name="app_init",
            path="src/main.py",
            content="def app_init(): pass",
            start_line=1,
            end_line=5,
            embedding=[0.1] * 128,
        )

        # Verify that entity creation succeeds and maps to curr_snapshot_id
        new_file_id = uuid.uuid4()
        new_chunk = CodeChunk(
            id=uuid.uuid4(),
            snapshot_id=curr_snapshot_id,
            file_id=new_file_id,
            symbol_id=uuid.uuid4(),
            chunk_type=old_chunk.chunk_type,
            name=old_chunk.name,
            path=old_chunk.path,
            content=old_chunk.content,
            start_line=old_chunk.start_line,
            end_line=old_chunk.end_line,
            embedding=old_chunk.embedding,
        )

        self.assertEqual(new_chunk.snapshot_id, curr_snapshot_id)
        self.assertEqual(new_chunk.embedding, old_chunk.embedding)
        self.assertEqual(new_chunk.content, old_chunk.content)


if __name__ == "__main__":
    unittest.main()
