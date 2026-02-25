"""Tests for boundary and edge case conditions."""

import tempfile
from pathlib import Path

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
        text = "\U0001f600"  # Grinning face emoji
        assert estimate_tokens(text) == 1


class TestFileSizeCheck:
    """Tests for file-size limits enforced in check_file."""

    def test_max_file_exactly_at_limit(self):
        """_MAX_FILE_BYTES not flagged."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_bytes(b"x" * _MAX_FILE_BYTES)
            result = _mod_estimate.check_file(f)
            assert result["exists"] is True
            assert result.get("error") != "file too large to check"

    def test_max_file_one_over_limit(self):
        """_MAX_FILE_BYTES+1 flagged."""
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
        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp) / ".claude" / "memory"
            memory.mkdir(parents=True)
            # 4-byte chunks map 1:1 with tokens (prose = 4 bytes/token), no remainder.
            file_count = 4
            tokens_per_file = L2_TOTAL_BUDGET // file_count
            remainder = L2_TOTAL_BUDGET - tokens_per_file * file_count
            for i in range(file_count):
                extra = 1 if i < remainder else 0
                (memory / f"file{i}.md").write_text("abcd" * (tokens_per_file + extra))
            result = _mod_estimate.validate(tmp)
            assert result["valid"] is True

    def test_one_over_budget_is_invalid(self):
        """Total = L2_TOTAL+1 = invalid."""
        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp) / ".claude" / "memory"
            memory.mkdir(parents=True)
            # 4-byte chunks map 1:1 with tokens (prose = 4 bytes/token), no remainder.
            file_count = 4
            tokens_per_file = L2_TOTAL_BUDGET // file_count
            remainder = L2_TOTAL_BUDGET - tokens_per_file * file_count
            for i in range(file_count):
                extra = 1 if i < remainder else 0
                (memory / f"file{i}.md").write_text("abcd" * (tokens_per_file + extra))
            # Add one extra token to push total over the budget by exactly 1.
            # Pick a file that didn't receive the remainder (i >= remainder).
            target_file = remainder if remainder < file_count else 0
            (memory / f"file{target_file}.md").write_text(
                "abcd" * (tokens_per_file + 1)
            )
            result = _mod_estimate.validate(tmp)
            assert result["valid"] is False
            assert any("L2 total" in e for e in result["errors"])


class TestDetectBoundary:
    """Tests for detection threshold boundaries."""

    def test_compose_exactly_at_threshold(self):
        """3 services = microservices."""
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
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compose = tmp_path / "docker-compose.yml"
            compose.write_text(
                "services:\n  api:\n    build: ./api\n  worker:\n    build: ./worker\n"
            )
            result = detect_repo_type(str(tmp))
            assert result["type"] != "microservices"

    def test_exactly_three_dockerfiles(self):
        """3 Dockerfiles counted."""
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
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Single weak signal (score 1): go.mod alone (not counted as monorepo)
            # go.mod is a library marker, adds +1
            (tmp_path / "go.mod").write_text("module github.com/user/test")
            result = detect_repo_type(str(tmp))
            # go.mod alone gives +1 to library, but that's not enough to beat single_app default
            # The code checks: if indicators[repo_type] < 2 -> default to single_app
            assert result["type"] == "single_app"
