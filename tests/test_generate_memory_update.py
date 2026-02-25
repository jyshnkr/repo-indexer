"""Tests for generate-memory-update.py."""

import json
import pathlib
import subprocess
import sys

import pytest
from helpers import import_script

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "skills" / "repo-indexer" / "scripts" / "generate-memory-update.py"
)

_mod = import_script("generate-memory-update")
generate_memory_update = _mod.generate_memory_update


class TestGenerateMemoryUpdate:
    def test_basic_output_contains_repo_name(self):
        result = generate_memory_update(
            repo_name="my-app",
            repo_type="single_app",
            tech_stack=["Python", "FastAPI"],
            key_modules=["api", "models"],
            patterns=["REST"],
        )
        assert "my-app" in result

    def test_output_contains_repo_type(self):
        result = generate_memory_update(
            repo_name="svc",
            repo_type="microservices",
            tech_stack=["Go"],
            key_modules=["handlers"],
            patterns=[],
        )
        assert "microservices" in result

    def test_tech_stack_limited_to_five(self):
        stack = ["A", "B", "C", "D", "E", "F", "G"]
        result = generate_memory_update(
            repo_name="r",
            repo_type="library",
            tech_stack=stack,
            key_modules=["x"],
            patterns=[],
        )
        assert "F" not in result
        assert "G" not in result

    def test_key_modules_limited_to_four(self):
        modules = ["m1", "m2", "m3", "m4", "m5"]
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=modules,
            patterns=[],
        )
        assert "m5" not in result

    def test_patterns_limited_to_three(self):
        patterns = ["P1", "P2", "P3", "P4"]
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=patterns,
        )
        assert "P4" not in result

    def test_empty_patterns_omitted(self):
        result = generate_memory_update(
            repo_name="r",
            repo_type="library",
            tech_stack=["Rust"],
            key_modules=["lib"],
            patterns=[],
        )
        assert "patterns:" not in result

    def test_contains_how_to_add_section(self):
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=["REST"],
        )
        assert "How to add" in result

    def test_summary_included_in_output(self):
        """B2: Non-empty summary should appear in the generated output."""
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
            summary="A test project",
        )
        assert "A test project" in result

    def test_empty_summary_omitted(self):
        """B2: Empty summary should not add an entry."""
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
            summary="",
        )
        assert "summary:" not in result

    def test_summary_non_string_rejected(self):
        """Non-string summary should be rejected by the CLI."""
        payload = json.dumps({
            "repo_name": "r",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
            "summary": 123,
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'summary' must be a string" in result.stderr

    def test_tech_stack_non_string_element_rejected(self):
        """Non-string element in tech_stack should be rejected by the CLI."""
        payload = json.dumps({
            "repo_name": "r",
            "repo_type": "single_app",
            "tech_stack": ["Python", 3],  # 3 is int, not string
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'tech_stack' elements must be strings" in result.stderr

    def test_key_modules_non_string_element_rejected(self):
        """Non-string element in key_modules should be rejected by the CLI."""
        payload = json.dumps({
            "repo_name": "r",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m", 123],  # 123 is int, not string
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'key_modules' elements must be strings" in result.stderr

    def test_patterns_non_string_element_rejected(self):
        """Non-string element in patterns should be rejected by the CLI."""
        payload = json.dumps({
            "repo_name": "r",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": ["REST", True],  # True is bool, not string
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'patterns' elements must be strings" in result.stderr

    def test_today_date_included(self):
        from datetime import date
        today = date.today().isoformat()
        result = generate_memory_update(
            repo_name="dated-repo",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["core"],
            patterns=[],
        )
        assert today in result


class TestCLIErrorPaths:
    """Tests for CLI error handling in generate-memory-update.py."""

    def test_invalid_json_exits_nonzero(self):
        """Malformed JSON → exit 1, 'Invalid JSON' in stderr."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), "not valid json {{"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "Invalid JSON" in result.stderr

    def test_non_dict_json_exits_nonzero(self):
        """Array JSON → exit 1, 'must be an object'."""
        payload = json.dumps(["item1", "item2"])
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "must be an object" in result.stderr

    def test_missing_required_keys_exits_nonzero(self):
        """Partial keys → exit 1, 'Missing required keys'."""
        payload = json.dumps({
            "repo_name": "test",
            # missing repo_type, tech_stack, key_modules, patterns
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "Missing required keys" in result.stderr

    def test_repo_name_non_string(self):
        """Non-string repo_name → exit 1."""
        payload = json.dumps({
            "repo_name": 123,
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'repo_name' must be a string" in result.stderr

    def test_repo_type_non_string(self):
        """Non-string repo_type → exit 1."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": ["single_app"],  # wrong type
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'repo_type' must be a string" in result.stderr

    def test_tech_stack_not_list(self):
        """String instead of list → exit 1."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": "single_app",
            "tech_stack": "Python",  # wrong type - should be list
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'tech_stack' must be an array" in result.stderr

    def test_no_args_runs_demo(self):
        """No args → exit 0, contains 'api-gateway'."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "api-gateway" in result.stdout

    def test_extra_keys_are_filtered(self):
        """Extra JSON keys silently stripped."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
            "extra_key": "should be filtered",
            "another_extra": 123,
        })
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "extra_key" not in result.stdout
        assert "another_extra" not in result.stdout


class TestEdgeCases:
    """Selected edge case and format tests merged from eliminated test files."""

    @pytest.fixture
    def _cli_result(self):
        """Shared CLI invocation result for output format tests."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
        })
        return subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), payload],
            capture_output=True, text=True,
        )

    def test_very_long_repo_name_no_crash(self):
        """10000-char name → no crash, name in output."""
        long_name = "a" * 10000
        result = generate_memory_update(
            repo_name=long_name,
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
        )
        assert long_name in result

    def test_unicode_cjk_in_repo_name(self):
        """CJK characters in repo_name → no crash."""
        result = generate_memory_update(
            repo_name="プロジェクト",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
        )
        assert "プロジェクト" in result

    def test_cli_output_format(self, _cli_result):
        """CLI output contains Claude Memory header and ``` code fence markers."""
        assert _cli_result.returncode == 0
        assert "Claude Memory" in _cli_result.stdout or "Memory Update" in _cli_result.stdout
        assert "```" in _cli_result.stdout


class TestEmptyInputs:
    """Tests for empty list handling."""

    def test_empty_tech_stack_list(self):
        """Empty list doesn't crash."""
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=[],
            key_modules=["m"],
            patterns=[],
        )
        assert "r" in result

    def test_empty_key_modules_list(self):
        """Empty list doesn't crash."""
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=[],
            patterns=[],
        )
        assert "r" in result

    def test_all_empty_optional_fields(self):
        """patterns=[], summary='' → minimal output."""
        result = generate_memory_update(
            repo_name="r",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
            summary="",
        )
        assert "patterns:" not in result
        assert "summary:" not in result
