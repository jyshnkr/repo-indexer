"""Shared pytest fixtures for repo-indexer test suite."""

import pytest


@pytest.fixture
def tmp_repo(tmp_path):
    """Empty temporary directory simulating a repo root."""
    return tmp_path


@pytest.fixture
def single_app_repo(tmp_path):
    """Minimal single-app repo layout."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# main")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'app'\n")
    return tmp_path


@pytest.fixture
def monorepo(tmp_path):
    """Repo with pnpm-workspace.yaml and packages/ dir."""
    (tmp_path / "packages").mkdir()
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
    return tmp_path


@pytest.fixture
def microservices_repo(tmp_path):
    """Repo with multiple Dockerfiles."""
    for svc in ("api", "worker", "gateway"):
        svc_dir = tmp_path / svc
        svc_dir.mkdir()
        (svc_dir / "Dockerfile").write_text(f"FROM python:3.11\n# {svc}\n")
    return tmp_path


@pytest.fixture
def library_repo(tmp_path):
    """Repo that looks like a Python library."""
    (tmp_path / "src").mkdir()
    (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='lib')\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mylib'\n")
    return tmp_path


@pytest.fixture
def claude_dir(tmp_path):
    """Repo with a .claude/memory/ structure."""
    memory = tmp_path / ".claude" / "memory"
    memory.mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text("# Boot\nProject: test\n")
    (memory / "architecture.md").write_text("# Architecture\n" + "word " * 50)
    (memory / "conventions.md").write_text("# Conventions\n" + "word " * 30)
    return tmp_path


@pytest.fixture
def full_pipeline_repo(tmp_path):
    """Repo with .claude/ structure for all pipeline stages."""
    memory = tmp_path / ".claude" / "memory"
    memory.mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text("# Boot\nProject: test\n")
    (memory / "architecture.md").write_text("# Architecture\n" + "word " * 40)
    (memory / "conventions.md").write_text("# Conventions\n" + "word " * 30)
    (memory / "glossary.md").write_text("# Glossary\n- term: definition\n")
    # Also add source files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    return tmp_path


@pytest.fixture
def mixed_signals_repo(tmp_path):
    """Repo with both monorepo and microservices signals."""
    # Monorepo signals
    (tmp_path / "packages").mkdir()
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
    # Microservices signals (Dockerfiles)
    for svc in ("api", "worker", "gateway"):
        svc_dir = tmp_path / svc
        svc_dir.mkdir()
        (svc_dir / "Dockerfile").write_text(f"FROM python:3.11\n# {svc}\n")
    return tmp_path
