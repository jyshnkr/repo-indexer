"""Integration test: full 4-script workflow against a sample library repo."""

import json
import pathlib
import subprocess
import sys

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skills" / "repo-indexer" / "scripts"

_DETECT = _SCRIPTS / "detect-repo-type.py"
_ESTIMATE = _SCRIPTS / "estimate-tokens.py"
_GENERATE = _SCRIPTS / "generate-memory-update.py"


@pytest.fixture
def sample_library(tmp_path):
    """A minimal Python library with .claude/ memory files, ready for workflow."""
    # Source layout
    (tmp_path / "mylib").mkdir()
    (tmp_path / "mylib" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (tmp_path / "mylib" / "core.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'mylib'\nversion = '1.0.0'\n"
    )
    (tmp_path / "README.md").write_text("# mylib\nA sample library.\n")

    # .claude/memory/ structure
    memory = tmp_path / ".claude" / "memory"
    memory.mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text(
        "# mylib\nA sample Python library.\n\n<!-- USER -->\n"
    )
    (memory / "architecture.md").write_text("# Architecture\n" + "word " * 40 + "\n")
    (memory / "conventions.md").write_text("# Conventions\n" + "word " * 20 + "\n")
    (memory / "glossary.md").write_text("# Glossary\n- term: definition\n")

    return tmp_path


class TestFullWorkflow:
    """Exercise the three Python scripts in the intended order."""

    def test_phase2_detect_identifies_library(self, sample_library):
        """Phase 2: detect-repo-type.py correctly classifies the sample repo."""
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(sample_library)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.startswith("TYPE: library"), (
            f"Expected library, got: {result.stdout!r}"
        )

    def test_phase5_estimate_passes_budget(self, sample_library):
        """Phase 5: estimate-tokens.py validates that all files are within budget."""
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(sample_library)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"Token budget validation failed:\n{result.stdout}\n{result.stderr}"
        )
        assert "Valid: True" in result.stdout

    def test_phase5_generate_produces_memory_snippet(self):
        """Phase 5: generate-memory-update.py produces the expected memory block."""
        payload = json.dumps({
            "repo_name": "mylib",
            "repo_type": "library",
            "tech_stack": ["Python 3.9+"],
            "key_modules": ["core"],
            "patterns": ["stdlib-only"],
        })
        result = subprocess.run(
            [sys.executable, str(_GENERATE), payload],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "Repo: mylib" in result.stdout
        assert "mylib indexed" in result.stdout
        assert "library" in result.stdout

    def test_detect_then_generate_pipeline(self, sample_library):
        """Detect type, feed it into generate — full pipeline without manual input."""
        # Phase 2: detect
        detect_result = subprocess.run(
            [sys.executable, str(_DETECT), str(sample_library)],
            capture_output=True, text=True,
        )
        assert detect_result.returncode == 0
        # Parse "TYPE: library (confidence: 1.0)"
        repo_type = detect_result.stdout.split()[1]

        # Phase 6: generate using detected type
        payload = json.dumps({
            "repo_name": sample_library.name,
            "repo_type": repo_type,
            "tech_stack": ["Python 3.9+"],
            "key_modules": ["mylib.core"],
            "patterns": ["stdlib-only"],
        })
        gen_result = subprocess.run(
            [sys.executable, str(_GENERATE), payload],
            capture_output=True, text=True,
        )
        assert gen_result.returncode == 0, gen_result.stderr
        assert repo_type in gen_result.stdout

    def test_oversized_claude_md_fails_estimate(self, sample_library):
        """Phase 5 must fail when CLAUDE.md exceeds its 500-token budget."""
        # Write a CLAUDE.md that is clearly over 500 tokens (2000+ chars > 500*4 bytes)
        (sample_library / "CLAUDE.md").write_text("x " * 1200)
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(sample_library)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0, (
            "estimate-tokens.py should exit non-zero when CLAUDE.md is over budget"
        )
        assert "FAIL" in result.stdout or "over" in result.stdout.lower()


class TestNonLibraryWorkflows:
    """Integration tests for non-library repo types."""

    def test_monorepo_detect_estimate(self, tmp_path):
        """Detect and estimate pipeline for monorepo type."""
        # Set up monorepo structure
        (tmp_path / "packages").mkdir()
        (tmp_path / "packages" / "pkg1").mkdir()
        (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        (tmp_path / "CLAUDE.md").write_text("# Test Monorepo\n")

        # Detect
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "TYPE: monorepo" in result.stdout

        # Estimate
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_microservices_detect_estimate(self, tmp_path):
        """Detect and estimate pipeline for microservices type."""
        # Set up microservices structure
        for svc in ("api", "worker", "gateway"):
            svc_dir = tmp_path / svc
            svc_dir.mkdir()
            (svc_dir / "Dockerfile").write_text("FROM python:3.11\n")
        (tmp_path / "CLAUDE.md").write_text("# Test Microservices\n")

        # Detect
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "TYPE: microservices" in result.stdout

        # Estimate
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_single_app_detect_estimate(self, tmp_path):
        """Detect and estimate pipeline for single_app type."""
        # Set up single app structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
        (tmp_path / "CLAUDE.md").write_text("# Test App\n")

        # Detect
        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "TYPE: " in result.stdout

        # Estimate
        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0


class TestReindexing:
    """Integration tests for reindexing scenarios."""

    def test_type_changes_on_structure_change(self, tmp_path):
        """Library→monorepo after adding packages/."""
        # Start as library
        (tmp_path / "src").mkdir()
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert "TYPE: library" in result.stdout

        # Add monorepo structure
        (tmp_path / "packages").mkdir()

        result = subprocess.run(
            [sys.executable, str(_DETECT), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert "TYPE: monorepo" in result.stdout

    def test_budget_fails_after_file_growth(self, tmp_path):
        """Valid→invalid after growing memory file."""
        memory = tmp_path / ".claude" / "memory"
        memory.mkdir(parents=True)
        (tmp_path / "CLAUDE.md").write_text("# Test\n")

        # Start with valid file
        (memory / "architecture.md").write_text("word " * 100)

        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Valid: True" in result.stdout

        # Grow file over budget (5000 tokens = 20000 bytes = 4000 "word ")
        (memory / "architecture.md").write_text("word " * 5000)

        result = subprocess.run(
            [sys.executable, str(_ESTIMATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "Valid: False" in result.stdout
