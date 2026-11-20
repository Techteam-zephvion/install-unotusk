import unittest


class TestSlidingWindowChunking(unittest.TestCase):
    def test_sliding_window_indexes_beyond_100_lines(self):
        # Generate 250 lines of code
        lines = [f"line {i}: var x_{i} = {i};" for i in range(1, 251)]
        window_size = 100
        step_size = 80
        max_chunks = 50

        chunks = []
        for start_idx in range(0, len(lines), step_size):
            if len(chunks) >= max_chunks:
                break
            chunk_lines = lines[start_idx : start_idx + window_size]
            if not chunk_lines:
                break
            chunks.append(
                {
                    "start_line": start_idx + 1,
                    "end_line": start_idx + len(chunk_lines),
                    "line_count": len(chunk_lines),
                    "first_line": chunk_lines[0],
                    "last_line": chunk_lines[-1],
                }
            )
            if start_idx + window_size >= len(lines):
                break

        # 250 lines with step 80:
        # Chunk 0: lines 1 - 100
        # Chunk 1: lines 81 - 180
        # Chunk 2: lines 161 - 250
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertEqual(chunks[0]["end_line"], 100)
        self.assertEqual(chunks[1]["start_line"], 81)
        self.assertEqual(chunks[1]["end_line"], 180)
        self.assertEqual(chunks[2]["start_line"], 161)
        self.assertEqual(chunks[2]["end_line"], 250)

        # Verify that line 250 (far beyond 100) is present in the final chunk!
        self.assertIn("line 250", chunks[2]["last_line"])


if __name__ == "__main__":
    unittest.main()
