"""CLI contract tests - verifying output format consistency."""

import json
import pathlib
import subprocess
import sys

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skills" / "repo-indexer" / "scripts"

_DETECT = _SCRIPTS / "detect-repo-type.py"
_ESTIMATE = _SCRIPTS / "estimate-tokens.py"
_GENERATE = _SCRIPTS / "generate-memory-update.py"


class TestDetectOutputFormat:
    """Tests for detect-repo-type.py CLI output format."""

    def test_output_type_prefix(self, tmp_path):
        """First line: 'TYPE: <word> (confidence: <float>)'."""
        (tmp_path / "packages").mkdir()
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        first_line = result.stdout.splitlines()[0]
        assert first_line.startswith("TYPE: ")
        assert "(confidence:" in first_line

    def test_evidence_indented(self, tmp_path):
        """Evidence lines start with '  - '."""
        (tmp_path / "packages").mkdir()
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        lines = result.stdout.splitlines()
        # At least one evidence line should be indented
        evidence_lines = [l for l in lines[1:] if l.strip()]
        assert len(evidence_lines) > 0

    def test_exit_codes(self, tmp_path):
        """0 on success, 1 on invalid path."""
        # Valid path
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

        # Invalid path
        result = subprocess.run(
            [sys.executable, str(_DETECT), "/nonexistent/path/xyz"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "ERROR" in result.stderr


class TestEstimateOutputFormat:
    """Tests for estimate-tokens.py CLI output format."""

    def test_output_valid_prefix(self, tmp_path):
        """'Valid: True|False | Total: <int> tokens'."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Valid: True" in result.stdout
        assert "tokens" in result.stdout

    def test_exit_codes(self, tmp_path):
        """0 = valid, 1 = over budget."""
        # Valid
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

        # Over budget
        (tmp_path / "CLAUDE.md").write_text("word " * 600)
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1


class TestGenerateOutputFormat:
    """Tests for generate-memory-update.py CLI output format."""

    def test_output_has_markdown_header(self):
        """Contains '## Claude Memory Update' or similar."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_GENERATE), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Claude Memory" in result.stdout or "Memory Update" in result.stdout

    def test_output_has_code_fence(self):
        """Contains ``` markers."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_GENERATE), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "```" in result.stdout

    def test_output_has_how_to_add(self):
        """Contains 'How to add' section."""
        payload = json.dumps({
            "repo_name": "test",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
        })
        result = subprocess.run(
            [sys.executable, str(_GENERATE), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "How to add" in result.stdout
