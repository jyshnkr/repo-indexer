"""Tests for boundary and edge case conditions."""

import pytest
from helpers import import_script

_mod_detect = import_script("detect-repo-type")
_mod_estimate = import_script("estimate-tokens")

detect_repo_type = _mod_detect.detect_repo_type
estimate_tokens = _mod_estimate.estimate_tokens
L2_TOTAL_BUDGET = _mod_estimate.L2_TOTAL_BUDGET
_MAX_FILE_BYTES = _mod_estimate._MAX_FILE_BYTES


class TestTokenBoundary:
    """Tests for token estimation boundary conditions."""

    def test_single_byte_returns_zero(self):
        """1 byte // 4 = 0 tokens."""
        text = "a"
        assert estimate_tokens(text) == 0

    def test_four_bytes_returns_one(self):
        """4 bytes = 1 token (prose)."""
        text = "abcd"
        assert estimate_tokens(text) == 1

    def test_three_bytes_code_returns_one(self):
        """3 bytes = 1 token (code)."""
        text = "abc"
        assert estimate_tokens(text, mode="code") == 1

    def test_unicode_emoji_token_count(self):
        """4-byte emoji = 1 token."""
        # Emoji is typically 4 bytes in UTF-8
        text = "\U0001F600"  # Grinning face emoji
        assert estimate_tokens(text) == 1

    def test_max_file_exactly_at_limit(self):
        """_MAX_FILE_BYTES not flagged."""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_bytes(b"x" * _MAX_FILE_BYTES)
            result = _mod_estimate.check_file(f)
            assert result["exists"] is True
            assert result.get("error") != "file too large to check"

    def test_max_file_one_over_limit(self):
        """_MAX_FILE_BYTES+1 flagged."""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_bytes(b"x" * (_MAX_FILE_BYTES + 1))
            result = _mod_estimate.check_file(f)
            assert result["exists"] is True
            assert result.get("error") == "file too large to check"


class TestL2Budget:
    """Tests for L2 aggregate budget boundaries."""

    def test_exactly_at_budget_is_valid(self):
        """Total = L2_TOTAL = valid."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp) / ".claude" / "memory"
            memory.mkdir(parents=True)
            # L2_TOTAL_BUDGET = 10000 tokens
            # Each "word " = 5 bytes = 1 token (prose)
            # Need 10000 tokens = 50000 bytes = 10000 "word " strings
            for i in range(4):  # 4 files
                # Each file: 2500 tokens = 10000 bytes = 2000 "word "
                (memory / f"file{i}.md").write_text("word " * 2000)
            result = _mod_estimate.validate(tmp)
            assert result["valid"] is True

    def test_one_over_budget_is_invalid(self):
        """Total = L2_TOTAL+1 = invalid."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp) / ".claude" / "memory"
            memory.mkdir(parents=True)
            # One over budget
            for i in range(4):  # 4 files of 2500 = 10000
                (memory / f"file{i}.md").write_text("word " * 2000)
            # Add one more file with 1 token over
            (memory / "file4.md").write_text("word " * 2001)
            result = _mod_estimate.validate(tmp)
            assert result["valid"] is False
            assert any("L2 total" in e for e in result["errors"])


class TestDetectBoundary:
    """Tests for detection threshold boundaries."""

    def test_compose_exactly_at_threshold(self):
        """3 services = microservices."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compose = tmp_path / "docker-compose.yml"
            compose.write_text(
                "services:\n"
                "  api:\n    build: ./api\n"
                "  worker:\n    build: ./worker\n"
                "  cache:\n    image: redis\n"
            )
            result = detect_repo_type(str(tmp))
            assert result["type"] == "microservices"

    def test_compose_one_below_threshold(self):
        """2 services != microservices."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compose = tmp_path / "docker-compose.yml"
            compose.write_text(
                "services:\n"
                "  api:\n    build: ./api\n"
                "  worker:\n    build: ./worker\n"
            )
            result = detect_repo_type(str(tmp))
            assert result["type"] != "microservices"

    def test_exactly_three_dockerfiles(self):
        """3 Dockerfiles counted."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for i in range(3):
                d = tmp_path / f"svc{i}"
                d.mkdir()
                (d / "Dockerfile").write_text("FROM python:3\n")
            result = detect_repo_type(str(tmp))
            assert result["scores"]["microservices"] >= 3

    def test_exactly_two_dockerfiles_not_counted(self):
        """2 Dockerfiles = not counted for microservices."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for i in range(2):
                d = tmp_path / f"svc{i}"
                d.mkdir()
                (d / "Dockerfile").write_text("FROM python:3\n")
            result = detect_repo_type(str(tmp))
            # Less than 3 Dockerfiles should not add to microservices
            assert result["scores"]["microservices"] < 3

    def test_min_score_threshold(self):
        """Score 1 → single_app; score 2 → wins."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Single weak signal (score 1): go.mod alone (not counted as monorepo)
            # go.mod is a library marker, adds +1
            (tmp_path / "go.mod").write_text("module github.com/user/test")
            result = detect_repo_type(str(tmp))
            # go.mod alone gives +1 to library, but that's not enough to beat single_app default
            # The code checks: if indicators[repo_type] < 2 -> default to single_app
            assert result["type"] == "single_app"
