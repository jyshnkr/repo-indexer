"""Tests for detect-repo-type.py."""

import os

import pytest
from helpers import import_script

_mod = import_script("detect-repo-type")
detect_repo_type = _mod.detect_repo_type
_find_dockerfiles = _mod._find_dockerfiles


class TestDetectRepoType:
    def test_single_app_default(self, tmp_repo):
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "single_app"
        assert result["confidence"] == 0.5

    def test_monorepo_via_pnpm_workspace(self, monorepo):
        result = detect_repo_type(str(monorepo))
        assert result["type"] == "monorepo"
        assert result["confidence"] > 0.5

    def test_monorepo_via_packages_dir(self, tmp_repo):
        (tmp_repo / "packages").mkdir()
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "monorepo"

    def test_monorepo_via_package_json_workspaces(self, tmp_repo):
        (tmp_repo / "package.json").write_text('{"workspaces": ["packages/*"]}')
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "monorepo"

    def test_microservices_multiple_dockerfiles(self, microservices_repo):
        result = detect_repo_type(str(microservices_repo))
        assert result["type"] == "microservices"

    def test_microservices_docker_compose(self, tmp_repo):
        compose = (
            "services:\n"
            "  api:\n    build: ./api\n"
            "  worker:\n    build: ./worker\n"
            "  db:\n    build: ./db\n"
        )
        (tmp_repo / "docker-compose.yml").write_text(compose)
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "microservices"

    def test_library_detection(self, library_repo):
        result = detect_repo_type(str(library_repo))
        assert result["type"] == "library"

    def test_returns_evidence_list(self, monorepo):
        result = detect_repo_type(str(monorepo))
        assert isinstance(result["evidence"], list)
        assert len(result["evidence"]) > 0

    def test_returns_scores_dict(self, tmp_repo):
        result = detect_repo_type(str(tmp_repo))
        assert "scores" in result
        assert set(result["scores"].keys()) == {"monorepo", "microservices", "single_app", "library"}

    def test_confidence_between_zero_and_one(self, monorepo):
        result = detect_repo_type(str(monorepo))
        assert 0.0 <= result["confidence"] <= 1.0

    def test_invalid_package_json_ignored(self, tmp_repo):
        (tmp_repo / "package.json").write_text("not valid json {{")
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "single_app"  # Falls back gracefully

    def test_docker_compose_ignores_commented_build(self, tmp_repo):
        """B1: build: in comments should not be counted as services."""
        compose = (
            "services:\n"
            "  api:\n    build: ./api\n"
            "  worker:\n    build: ./worker\n"
            "  db:\n    build: ./db\n"
            "  # TODO: build: another service later\n"
            "  cache:\n    image: redis  # build: custom later\n"
        )
        (tmp_repo / "docker-compose.yml").write_text(compose)
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "microservices"
        # Verify the evidence string shows 3 services, not 5
        compose_evidence = [e for e in result["evidence"] if "docker-compose" in e]
        assert len(compose_evidence) == 1
        assert "3 services" in compose_evidence[0]

    def test_docker_compose_below_threshold_with_comments(self, tmp_repo):
        """B1: Commented build: lines should not push count above threshold."""
        compose = (
            "services:\n"
            "  api:\n    build: ./api\n"
            "  worker:\n    build: ./worker\n"
            "  # build: fake1\n"
            "  # build: fake2\n"
        )
        (tmp_repo / "docker-compose.yml").write_text(compose)
        result = detect_repo_type(str(tmp_repo))
        # Only 2 real services, below MIN_SERVICES_FOR_MICROSERVICES=3
        compose_evidence = [e for e in result["evidence"] if "docker-compose" in e]
        assert len(compose_evidence) == 0

    @pytest.mark.skipif(os.getuid() == 0, reason="Test requires non-root to enforce permissions")
    def test_oserror_on_package_json_warns_stderr(self, tmp_repo, capsys):
        """B4: OSError reading package.json should warn to stderr, not silently pass."""
        pkg = tmp_repo / "package.json"
        pkg.write_text('{"workspaces": ["packages/*"]}')
        pkg.chmod(0o000)
        try:
            detect_repo_type(str(tmp_repo))
            captured = capsys.readouterr()
            assert "WARNING" in captured.err
            assert "package.json" in captured.err
        finally:
            pkg.chmod(0o644)

    @pytest.mark.skipif(os.getuid() == 0, reason="Test requires non-root to enforce permissions")
    def test_oserror_on_compose_warns_stderr(self, tmp_repo, capsys):
        """B4: OSError reading docker-compose.yml should warn to stderr."""
        compose = tmp_repo / "docker-compose.yml"
        compose.write_text("services:\n  api:\n    build: ./api\n")
        compose.chmod(0o000)
        try:
            detect_repo_type(str(tmp_repo))
            captured = capsys.readouterr()
            assert "WARNING" in captured.err
            assert "docker-compose" in captured.err
        finally:
            compose.chmod(0o644)


class TestFindDockerfiles:
    def test_finds_nested_dockerfiles(self, microservices_repo):
        found = _find_dockerfiles(microservices_repo)
        assert len(found) == 3

    def test_respects_max_depth(self, tmp_repo):
        # Create a Dockerfile 5 levels deep (beyond default MAX_DOCKERFILE_DEPTH=4)
        deep = tmp_repo / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "Dockerfile").write_text("FROM scratch")
        found = _find_dockerfiles(tmp_repo, max_depth=4)
        assert len(found) == 0

    def test_skips_node_modules(self, tmp_repo):
        nm = tmp_repo / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "Dockerfile").write_text("FROM node:18")
        found = _find_dockerfiles(tmp_repo)
        assert len(found) == 0

    def test_does_not_follow_symlinks(self, tmp_repo, tmp_path_factory):
        # Create a Dockerfile in a directory outside the repo root
        outside = tmp_path_factory.mktemp("outside")
        (outside / "Dockerfile").write_text("FROM scratch")
        link = tmp_repo / "linked"
        link.symlink_to(outside)
        found = _find_dockerfiles(tmp_repo)
        assert len(found) == 0
