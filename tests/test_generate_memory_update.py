"""Tests for generate-memory-update.py."""

import json
import pathlib
import subprocess
import sys

import pytest
from helpers import import_script

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
        script_path = (
            pathlib.Path(__file__).resolve().parent.parent
            / "skills" / "repo-indexer" / "scripts" / "generate-memory-update.py"
        )
        payload = json.dumps({
            "repo_name": "r",
            "repo_type": "single_app",
            "tech_stack": ["Python"],
            "key_modules": ["m"],
            "patterns": [],
            "summary": 123,
        })
        result = subprocess.run(
            [sys.executable, str(script_path), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "'summary' must be a string" in result.stderr

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
