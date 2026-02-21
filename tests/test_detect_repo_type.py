"""Tests for detect-repo-type.py."""

import os
import pathlib
import subprocess
import sys

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

    def test_invalid_package_json_ignored(self, tmp_repo, capsys):
        (tmp_repo / "package.json").write_text("not valid json {{")
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "single_app"  # Falls back gracefully
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

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
        # 3 build: services + 1 image: service = 4 real services.
        # Commented-out "build:" and "build:" after "#" must not be counted.
        compose_evidence = [e for e in result["evidence"] if "docker-compose" in e]
        assert len(compose_evidence) == 1
        assert "4 services" in compose_evidence[0]

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

    def test_src_only_without_lib_markers_favors_library(self, tmp_path):
        """A repo with only src/ (no lib markers) should classify as library, not single_app."""
        (tmp_path / "src").mkdir()
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "library"


class TestCLI:
    _script = (
        pathlib.Path(__file__).resolve().parent.parent
        / "skills" / "repo-indexer" / "scripts" / "detect-repo-type.py"
    )

    def test_invalid_path_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(self._script), "/nonexistent/path/abc123"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "ERROR" in result.stderr


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

    def test_max_dirs_visited_guard(self, tmp_repo):
        """Breadth guard prevents visiting more than MAX_DIRS_VISITED directories."""
        max_dirs = _mod.MAX_DIRS_VISITED
        # Create max_dirs + 1 flat subdirs, each with a Dockerfile
        for i in range(max_dirs + 1):
            d = tmp_repo / f"d{i:04d}"
            d.mkdir()
            (d / "Dockerfile").write_text("FROM scratch")
        found = _find_dockerfiles(tmp_repo)
        # The guard must have fired — not all Dockerfiles can be found
        assert len(found) < max_dirs + 1


class TestMicroservicesComposeVariants:
    @pytest.mark.parametrize("filename", [
        "docker-compose.yaml", "compose.yml", "compose.yaml",
    ])
    def test_compose_variants_detected(self, tmp_repo, filename):
        compose = "services:\n" + "".join(
            f"  svc{i}:\n    build: ./svc{i}\n" for i in range(3)
        )
        (tmp_repo / filename).write_text(compose)
        result = detect_repo_type(str(tmp_repo))
        assert result["type"] == "microservices"

    def test_compose_image_only_services_detected(self, tmp_path):
        """Services with image: (no build:) should count toward microservices."""
        compose = tmp_path / "docker-compose.yml"
        compose.write_text(
            "services:\n"
            "  redis:\n    image: redis:7\n"
            "  postgres:\n    image: postgres:16\n"
            "  nginx:\n    image: nginx:latest\n"
        )
        result = detect_repo_type(str(tmp_path))
        assert result["scores"]["microservices"] >= 3

    @pytest.mark.skipif(os.getuid() == 0, reason="Test requires non-root to enforce permissions")
    def test_compose_fallback_on_unreadable_first_variant(self, tmp_path):
        """When first compose variant is unreadable, should try the next one."""
        # docker-compose.yml exists but unreadable
        bad = tmp_path / "docker-compose.yml"
        bad.write_text("dummy")
        bad.chmod(0o000)
        # compose.yml is valid with 3 build: services
        good = tmp_path / "compose.yml"
        good.write_text(
            "services:\n"
            "  web:\n    build: ./web\n"
            "  api:\n    build: ./api\n"
            "  worker:\n    build: ./worker\n"
        )
        try:
            result = detect_repo_type(str(tmp_path))
        finally:
            bad.chmod(0o644)  # cleanup for tmp_path removal
        assert result["scores"]["microservices"] >= 3
