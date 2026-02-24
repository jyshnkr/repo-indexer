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

    @pytest.mark.skipif(not hasattr(os, "getuid") or os.getuid() == 0, reason="Test requires non-root to enforce permissions")
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

    @pytest.mark.skipif(not hasattr(os, "getuid") or os.getuid() == 0, reason="Test requires non-root to enforce permissions")
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

    def test_pyproject_toml_without_src_dir_is_library(self, tmp_path):
        """Flat-layout Python packages (pyproject.toml, no src/) must be detected as library."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mypkg'\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "library", (
            f"Expected library, got {result['type']}. Scores: {result['scores']}"
        )

    def test_setup_py_without_src_dir_is_library(self, tmp_path):
        """A repo with setup.py but no src/ dir should still be detected as library."""
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "library"

    def test_pyproject_toml_with_monorepo_markers_does_not_override(self, tmp_path):
        """pyproject.toml inside a monorepo should not cause library to win."""
        (tmp_path / "packages").mkdir()
        (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'root'\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_workspace_config_without_dirs_prevents_library_boost(self, tmp_path):
        """pnpm-workspace.yaml alone (no packages/ dir) must classify as monorepo, not library."""
        (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'root'\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo", (
            f"Expected monorepo, got {result['type']}. Scores: {result['scores']}"
        )


class TestBuildSystemDetection:
    def test_gradle_multi_project_is_monorepo(self, tmp_path):
        """settings.gradle present → Gradle multi-project → monorepo."""
        (tmp_path / "settings.gradle").write_text("rootProject.name = 'myapp'")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_gradle_single_project_not_monorepo(self, tmp_path):
        """build.gradle alone (no settings.gradle) should NOT score as monorepo."""
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] != "monorepo"

    def test_gradle_kts_multi_project_is_monorepo(self, tmp_path):
        """settings.gradle.kts present → Gradle multi-project → monorepo."""
        (tmp_path / "settings.gradle.kts").write_text("rootProject.name = \"myapp\"")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_bazel_workspace_is_monorepo(self, tmp_path):
        """WORKSPACE file present → Bazel workspace → monorepo."""
        (tmp_path / "WORKSPACE").write_text('workspace(name = "myproject")')
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_bazel_module_bazel_is_monorepo(self, tmp_path):
        """MODULE.bazel present → Bazel workspace → monorepo."""
        (tmp_path / "MODULE.bazel").write_text('module(name = "myproject")')
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_bazel_bazelrc_only_not_monorepo(self, tmp_path):
        """.bazelrc alone (no WORKSPACE) should NOT score as monorepo."""
        (tmp_path / ".bazelrc").write_text("build --jobs 4")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] != "monorepo"

    def test_nx_workspace_is_monorepo(self, tmp_path):
        """nx.json alone is sufficient to classify as monorepo."""
        (tmp_path / "nx.json").write_text('{"version": 3}')
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_go_work_is_monorepo(self, tmp_path):
        """go.work file → Go workspace → monorepo."""
        (tmp_path / "go.work").write_text("go 1.21\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_setup_cfg_without_src_is_library(self, tmp_path):
        """setup.cfg without src/ should be detected as library (flat-layout)."""
        (tmp_path / "setup.cfg").write_text("[metadata]\nname = mypkg\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "library", (
            f"Expected library, got {result['type']}. Scores: {result['scores']}"
        )


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

    @pytest.mark.skipif(not hasattr(os, "getuid") or os.getuid() == 0, reason="Test requires non-root to enforce permissions")
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


class TestMissingConfigFiles:
    """Tests for config files mentioned in plan: turbo.json, lerna.json, WORKSPACE.bazel."""

    def test_turbo_json_is_monorepo(self, tmp_path):
        """turbo.json scores monorepo +3."""
        (tmp_path / "turbo.json").write_text('{"tasks": {}}')
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"
        assert any("turbo.json" in e for e in result["evidence"])

    def test_lerna_json_is_monorepo(self, tmp_path):
        """lerna.json scores monorepo +3."""
        (tmp_path / "lerna.json").write_text('{"packages": ["packages/*"]}')
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"
        assert any("lerna.json" in e for e in result["evidence"])

    def test_workspace_bazel_variant(self, tmp_path):
        """WORKSPACE.bazel scores monorepo +3."""
        (tmp_path / "WORKSPACE.bazel").write_text('workspace(name = "myproject")')
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"
        assert any("WORKSPACE.bazel" in e for e in result["evidence"])


class TestIsolatedLibraryIndicators:
    """Tests for library indicators: Cargo.toml, go.mod."""

    def test_cargo_toml_scores_library(self, tmp_path):
        """Cargo.toml alone adds library score."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "mylib"')
        result = detect_repo_type(str(tmp_path))
        # Should score library, though may still be single_app due to low score
        assert result["scores"]["library"] >= 1

    def test_go_mod_scores_library(self, tmp_path):
        """go.mod alone adds library score."""
        (tmp_path / "go.mod").write_text('module github.com/user/mylib')
        result = detect_repo_type(str(tmp_path))
        assert result["scores"]["library"] >= 1

    def test_cargo_toml_with_src_is_library(self, tmp_path):
        """Cargo.toml + src/ = strong library."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "mylib"')
        (tmp_path / "src").mkdir()
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "library"


class TestMixedSignals:
    """Tests for conflicting repo markers."""

    def test_monorepo_beats_microservices(self, tmp_path):
        """Higher monorepo score wins over microservices."""
        (tmp_path / "packages").mkdir()
        (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        # Add 3 Dockerfiles to trigger microservices
        for svc in ("api", "worker", "gateway"):
            svc_dir = tmp_path / svc
            svc_dir.mkdir()
            (svc_dir / "Dockerfile").write_text("FROM python:3.11\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "monorepo"

    def test_microservices_beats_weak_monorepo(self, tmp_path):
        """Many services beat single dir marker."""
        # Single monorepo dir marker
        (tmp_path / "modules").mkdir()
        # But many dockerfiles for microservices
        for i in range(5):
            svc_dir = tmp_path / f"svc{i}"
            svc_dir.mkdir()
            (svc_dir / "Dockerfile").write_text("FROM python:3.11\n")
        result = detect_repo_type(str(tmp_path))
        assert result["type"] == "microservices"

    def test_all_categories_nonzero(self, tmp_path):
        """Max scorer wins when all score."""
        # Add monorepo, microservices, and library signals
        (tmp_path / "packages").mkdir()
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'app'\n")
        for i in range(3):
            svc_dir = tmp_path / f"svc{i}"
            svc_dir.mkdir()
            (svc_dir / "Dockerfile").write_text("FROM python:3.11\n")
        result = detect_repo_type(str(tmp_path))
        # At least monorepo, microservices, and library should have scores
        assert result["scores"]["monorepo"] > 0
        assert result["scores"]["microservices"] > 0
        assert result["scores"]["library"] > 0
        # Winner should be the max
        assert result["type"] == max(result["scores"], key=result["scores"].get)

    def test_tie_resolution(self, tmp_path):
        """Documents tie-breaking behavior - Python's max returns first occurrence."""
        # Add equal scores for monorepo and library
        (tmp_path / "packages").mkdir()  # +2 monorepo
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'app'\n")  # +1 library
        (tmp_path / "setup.py").write_text("from setuptools import setup\n")  # +1 library
        # Total: monorepo=2, library=2, microservices=0, single_app=0
        result = detect_repo_type(str(tmp_path))
        # Python's max with dict returns first key encountered - order in indicators dict
        assert result["type"] in ["monorepo", "library"]


class TestDirectoryMarkers:
    """Tests for individual monorepo directory markers."""

    def test_apps_dir_scores_monorepo(self, tmp_path):
        """apps/ directory detected."""
        (tmp_path / "apps").mkdir()
        result = detect_repo_type(str(tmp_path))
        assert any("apps/" in e for e in result["evidence"])
        assert result["scores"]["monorepo"] >= 2

    def test_libs_dir_scores_monorepo(self, tmp_path):
        """libs/ directory detected."""
        (tmp_path / "libs").mkdir()
        result = detect_repo_type(str(tmp_path))
        assert any("libs/" in e for e in result["evidence"])
        assert result["scores"]["monorepo"] >= 2

    def test_modules_dir_scores_monorepo(self, tmp_path):
        """modules/ directory detected."""
        (tmp_path / "modules").mkdir()
        result = detect_repo_type(str(tmp_path))
        assert any("modules/" in e for e in result["evidence"])
        assert result["scores"]["monorepo"] >= 2

    def test_services_dir_scores_monorepo(self, tmp_path):
        """services/ directory detected."""
        (tmp_path / "services").mkdir()
        result = detect_repo_type(str(tmp_path))
        assert any("services/" in e for e in result["evidence"])
        assert result["scores"]["monorepo"] >= 2


class TestSelfDetectionRegression:
    """Regression test: ensure this repo (repo-indexer) is correctly detected."""

    def test_self_detection_regression(self):
        """Run against this repo root → type should include library score."""
        import pathlib

        # Get the root of this repo
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        result = detect_repo_type(str(repo_root))
        # This repo is a library/plugin - should have library score
        assert result["scores"]["library"] > 0
