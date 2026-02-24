"""Performance regression tests."""

import time
import pytest
from helpers import import_script

_mod_detect = import_script("detect-repo-type")
_mod_estimate = import_script("estimate-tokens")

detect_repo_type = _mod_detect.detect_repo_type
_find_dockerfiles = _mod_detect._find_dockerfiles
validate = _mod_estimate.validate
MAX_DIRS_VISITED = _mod_detect.MAX_DIRS_VISITED


class TestPerformance:
    """Performance regression guards."""

    def test_detect_500_flat_dirs_under_5s(self, tmp_path):
        """Performance regression guard: 500 flat directories."""
        # Create 500 flat subdirectories (worst case for breadth-first)
        for i in range(500):
            d = tmp_path / f"dir{i:04d}"
            d.mkdir()
            (d / "file.txt").write_text("content")

        start = time.time()
        result = detect_repo_type(str(tmp_path))
        elapsed = time.time() - start

        assert elapsed < 5.0, f"detect took {elapsed:.2f}s, expected < 5s"
        assert result["type"] is not None

    def test_detect_deep_nesting_under_5s(self, tmp_path):
        """Performance regression guard: 10-level deep tree."""
        # Create deep nested structure
        current = tmp_path
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir()
            (current / "file.txt").write_text("content")

        start = time.time()
        result = detect_repo_type(str(tmp_path))
        elapsed = time.time() - start

        assert elapsed < 5.0, f"detect took {elapsed:.2f}s, expected < 5s"
        assert result["type"] is not None

    def test_find_dockerfiles_breadth_guard(self, tmp_path):
        """MAX_DIRS_VISITED stops traversal."""
        # Create more directories than MAX_DIRS_VISITED
        for i in range(MAX_DIRS_VISITED + 100):
            d = tmp_path / f"dir{i:04d}"
            d.mkdir()
            (d / "Dockerfile").write_text("FROM scratch\n")

        found = _find_dockerfiles(tmp_path)
        # Should not find all files due to breadth guard
        assert len(found) <= MAX_DIRS_VISITED

    def test_estimate_50_memory_files_under_2s(self, tmp_path):
        """Many files performance."""
        memory = tmp_path / ".claude" / "memory"
        memory.mkdir(parents=True)

        # Create 50 memory files
        for i in range(50):
            (memory / f"file{i}.md").write_text("word " * 100)

        start = time.time()
        result = validate(str(tmp_path))
        elapsed = time.time() - start

        assert elapsed < 2.0, f"validate took {elapsed:.2f}s, expected < 2s"
        assert result["total"] > 0

    def test_estimate_1mb_file_performance(self, tmp_path):
        """Large file read time."""
        large_file = tmp_path / "large.md"
        # Write 1MB file
        large_file.write_bytes(b"x" * 1_000_000)

        start = time.time()
        result = _mod_estimate.check_file(large_file)
        elapsed = time.time() - start

        # Should handle large file quickly (either skip or process)
        assert elapsed < 1.0, f"check_file took {elapsed:.2f}s, expected < 1s"
        # Should either return error for oversized or process it
        assert "error" in result or result["tokens"] > 0
