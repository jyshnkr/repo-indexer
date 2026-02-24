"""Tests for estimate-tokens.py."""

import os
import pathlib
import subprocess
import sys

import pytest
from helpers import import_script

_mod = import_script("estimate-tokens")
estimate_tokens = _mod.estimate_tokens
_guess_content_mode = _mod._guess_content_mode
check_file = _mod.check_file
validate = _mod.validate
L2_TOTAL_BUDGET = _mod.L2_TOTAL_BUDGET
BUDGETS = _mod.BUDGETS
_MAX_FILE_BYTES = _mod._MAX_FILE_BYTES


class TestEstimateTokens:
    def test_ascii_text(self):
        assert estimate_tokens("hello") == 1  # 5 bytes // 4 = 1

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_longer_text(self):
        text = "word " * 100  # 500 bytes
        assert estimate_tokens(text) == 125

    def test_multibyte_chars(self):
        # Each 'é' is 2 bytes in UTF-8
        text = "é" * 100  # 200 bytes
        tokens = estimate_tokens(text)
        assert tokens == 50  # 200 // 4

    def test_default_mode_unchanged(self):
        """Default mode must produce the same result as the original implementation."""
        text = "word " * 100  # 500 bytes
        assert estimate_tokens(text) == estimate_tokens(text, mode="default")

    def test_prose_mode_same_as_default(self):
        """Prose mode uses 4 bytes/token, identical to default."""
        text = "word " * 100  # 500 bytes
        assert estimate_tokens(text, mode="prose") == 125

    def test_code_mode_denser(self):
        """Code mode uses 3 bytes/token, yielding more tokens than default."""
        text = "x" * 300  # 300 bytes → 100 tokens at 3 bpt, 75 at 4 bpt
        assert estimate_tokens(text, mode="code") == 100
        assert estimate_tokens(text, mode="default") == 75

    def test_unknown_mode_falls_back_to_default(self):
        """Unknown mode strings should fall back to 4 bytes/token."""
        text = "word " * 100
        assert estimate_tokens(text, mode="unknown_mode") == 125


class TestGuessContentMode:
    def test_python_file_is_code(self, tmp_path):
        f = tmp_path / "script.py"
        assert _guess_content_mode(f) == "code"

    def test_markdown_file_is_prose(self, tmp_path):
        f = tmp_path / "README.md"
        assert _guess_content_mode(f) == "prose"

    def test_javascript_is_code(self, tmp_path):
        f = tmp_path / "app.js"
        assert _guess_content_mode(f) == "code"

    def test_no_extension_is_prose(self, tmp_path):
        f = tmp_path / "Makefile"
        assert _guess_content_mode(f) == "prose"

    def test_yaml_is_code(self, tmp_path):
        f = tmp_path / "config.yaml"
        assert _guess_content_mode(f) == "code"


class TestCheckFile:
    def test_missing_file(self, tmp_path):
        result = check_file(tmp_path / "nonexistent.md")
        assert result == {"exists": False}

    def test_file_within_budget(self, tmp_path):
        f = tmp_path / "CLAUDE.md"
        f.write_text("# Short\nMinimal content.\n")
        result = check_file(f)
        assert result["exists"] is True
        assert result["over"] is False
        assert result["budget"] == BUDGETS["CLAUDE.md"]

    def test_file_over_budget(self, tmp_path):
        f = tmp_path / "CLAUDE.md"
        # 600 * "word " = 3000 bytes > 500 token budget (2000 bytes)
        f.write_text("word " * 600)
        result = check_file(f)
        assert result["over"] is True
        assert result["tokens"] > 500

    def test_unknown_file_uses_default_budget(self, tmp_path):
        f = tmp_path / "custom.md"
        f.write_text("# Custom\nSome content.\n")
        result = check_file(f)
        assert result["budget"] == 5000  # MEMORY_DEFAULT_BUDGET

    def test_oversized_file_marked_over_budget(self, tmp_path):
        """S3: Files exceeding _MAX_FILE_BYTES should be flagged as over budget."""
        f = tmp_path / "CLAUDE.md"
        f.write_bytes(b"x" * 1_000_001)
        result = check_file(f)
        assert result["exists"] is True
        assert result["over"] is True
        assert result["pct"] is None
        assert result["error"] == "file too large to check"

    @pytest.mark.skipif(not hasattr(os, "getuid") or os.getuid() == 0, reason="Test requires non-root to enforce permissions")
    def test_file_read_error_handled(self, tmp_path):
        """OSError on read_text returns an error dict rather than raising."""
        f = tmp_path / "test.md"
        f.write_text("some content")
        f.chmod(0o000)
        try:
            result = check_file(f)
            assert result["exists"] is True
            assert "error" in result
            assert result["over"] is True
        finally:
            f.chmod(0o644)

    def test_file_exactly_at_max_bytes(self, tmp_path):
        """Boundary: file of exactly _MAX_FILE_BYTES is NOT treated as oversized (guard is >)."""
        f = tmp_path / "CLAUDE.md"
        f.write_bytes(b"x" * _MAX_FILE_BYTES)
        result = check_file(f)
        assert result["exists"] is True
        assert result.get("error") != "file too large to check"


class TestValidate:
    def test_empty_directory(self, tmp_repo):
        result = validate(str(tmp_repo))
        assert result["valid"] is True
        assert result["total"] == 0
        assert result["files"] == {}

    def test_claude_md_within_budget(self, tmp_repo):
        (tmp_repo / "CLAUDE.md").write_text("# Boot\nStack: Python\n")
        result = validate(str(tmp_repo))
        assert result["valid"] is True
        assert "CLAUDE.md" in result["files"]

    def test_claude_md_over_budget(self, tmp_repo):
        (tmp_repo / "CLAUDE.md").write_text("word " * 600)
        result = validate(str(tmp_repo))
        assert result["valid"] is False
        assert any("CLAUDE.md" in e for e in result["errors"])

    def test_memory_files_checked(self, claude_dir):
        result = validate(str(claude_dir))
        assert any(k.startswith("memory/") for k in result["files"])

    def test_aggregate_l2_budget_enforced(self, tmp_repo):
        memory = tmp_repo / ".claude" / "memory"
        memory.mkdir(parents=True)
        # 5 files × 2500 tokens each = 12500 tokens > L2_TOTAL_BUDGET (10000)
        # Each "word " is 5 bytes → 2000 words × 5 bytes = 10000 bytes // 4 = 2500 tokens
        for i in range(5):
            (memory / f"file{i}.md").write_text("word " * 2000)
        result = validate(str(tmp_repo))
        assert result["valid"] is False
        assert any("L2 total" in e for e in result["errors"])

    def test_aggregate_l2_budget_passes(self, claude_dir):
        result = validate(str(claude_dir))
        assert result["valid"] is True

    def test_oversized_file_fails_validation(self, tmp_repo):
        """S3: Oversized CLAUDE.md should cause validation failure."""
        f = tmp_repo / "CLAUDE.md"
        f.write_bytes(b"x" * 1_000_001)
        result = validate(str(tmp_repo))
        assert result["valid"] is False
        assert any("CLAUDE.md" in e for e in result["errors"])

    def test_validate_no_memory_directory(self, tmp_repo):
        """Repo with CLAUDE.md but no .claude/memory/ should validate successfully."""
        (tmp_repo / "CLAUDE.md").write_text("# Boot\nStack: Python\n")
        result = validate(str(tmp_repo))
        assert result["valid"] is True


class TestCLI:
    _script = (
        pathlib.Path(__file__).resolve().parent.parent
        / "skills" / "repo-indexer" / "scripts" / "estimate-tokens.py"
    )

    def test_invalid_path_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(self._script), "/nonexistent/path/abc123"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_valid_dir_exits_zero(self, tmp_repo):
        """Valid dir → exit 0."""
        result = subprocess.run(
            [sys.executable, str(self._script), str(tmp_repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Valid: True" in result.stdout

    def test_over_budget_exits_nonzero(self, tmp_repo):
        """Over budget → exit 1."""
        (tmp_repo / "CLAUDE.md").write_text("word " * 600)
        result = subprocess.run(
            [sys.executable, str(self._script), str(tmp_repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "Valid: False" in result.stdout


class TestContentModeExtensions:
    """Tests for content mode detection based on file extensions."""

    @pytest.mark.parametrize("ext,expected_mode", [
        # Code extensions
        (".ts", "code"),
        (".tsx", "code"),
        (".jsx", "code"),
        (".go", "code"),
        (".rs", "code"),
        (".java", "code"),
        (".c", "code"),
        (".cpp", "code"),
        (".sh", "code"),
        (".sql", "code"),
        (".json", "code"),
        (".html", "code"),
        (".css", "code"),
        (".toml", "code"),
        (".proto", "code"),
        # Prose extensions
        (".txt", "prose"),
        (".rst", "prose"),
    ])
    def test_extension_modes(self, tmp_path, ext, expected_mode):
        """Parametrized test for extension-based mode detection."""
        f = tmp_path / f"file{ext}"
        f.write_text("# content")
        assert _guess_content_mode(f) == expected_mode

    def test_case_insensitive_extension(self, tmp_path):
        """Extensions are case insensitive."""
        f = tmp_path / "file.PY"
        f.write_text("# content")
        assert _guess_content_mode(f) == "code"


class TestNamedBudgets:
    """Tests for named memory file budgets."""

    def test_architecture_md_uses_5000_budget(self, tmp_repo):
        """Named budget lookup for architecture.md."""
        memory = tmp_repo / ".claude" / "memory"
        memory.mkdir(parents=True)
        (memory / "architecture.md").write_text("word " * 500)
        assert "architecture.md" in BUDGETS, "architecture.md must have an explicit named budget"
        result = check_file(memory / "architecture.md")
        assert result["budget"] == 5000
        assert result["over"] is False

    def test_conventions_md_uses_3000_budget(self, tmp_repo):
        """Named budget lookup for conventions.md."""
        memory = tmp_repo / ".claude" / "memory"
        memory.mkdir(parents=True)
        (memory / "conventions.md").write_text("word " * 400)
        result = check_file(memory / "conventions.md")
        assert result["budget"] == 3000
        assert result["over"] is False

    def test_glossary_md_uses_2000_budget(self, tmp_repo):
        """Named budget lookup for glossary.md."""
        memory = tmp_repo / ".claude" / "memory"
        memory.mkdir(parents=True)
        (memory / "glossary.md").write_text("word " * 250)
        result = check_file(memory / "glossary.md")
        assert result["budget"] == 2000
        assert result["over"] is False

    def test_individual_memory_file_over_budget(self, tmp_repo):
        """architecture.md > 5000 tokens → over=True."""
        memory = tmp_repo / ".claude" / "memory"
        memory.mkdir(parents=True)
        # More than 5000 tokens: 5001 * 4 bytes = 20004 bytes = 4001 "word " + some
        # Actually: 5001 tokens * 4 bytes/token = 20004 bytes
        # "word " is 5 bytes, so 4001 tokens = 4001 * 5 = 20005 bytes = 4001 "word "
        # But we need over 5000, so let's use 5001 "word " = 5001 * 5 = 25005 bytes -> 6251 tokens
        (memory / "architecture.md").write_text("word " * 5001)
        result = check_file(memory / "architecture.md")
        assert result["over"] is True
