"""Tests for git-sync.sh."""

import os
import pathlib
import subprocess

import pytest

_SCRIPT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "skills" / "repo-indexer" / "scripts" / "git-sync.sh"
)

# Minimal git config so git doesn't complain in CI (no global config)
_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _run_sync(cwd, **kwargs):
    """Run git-sync.sh in cwd, returning CompletedProcess."""
    return subprocess.run(
        ["sh", str(_SCRIPT)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=_GIT_ENV,
        **kwargs,
    )


def _git(args, cwd):
    """Run a git command in cwd, raising on failure."""
    subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )


@pytest.fixture
def remote_repo(tmp_path_factory):
    """Bare git repo acting as 'origin', with a main branch and one commit."""
    remote = tmp_path_factory.mktemp("remote")
    _git(["init", "--bare", str(remote)], cwd=tmp_path_factory.getbasetemp())
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote)
    # Populate via a temporary working tree
    work = tmp_path_factory.mktemp("work")
    _git(["init", "-b", "main", str(work)], cwd=tmp_path_factory.getbasetemp())
    _git(["remote", "add", "origin", str(remote)], cwd=work)
    (work / "README.md").write_text("hello")
    _git(["add", "."], cwd=work)
    _git(["commit", "-m", "init"], cwd=work)
    _git(["push", "origin", "main"], cwd=work)
    return remote


@pytest.fixture
def local_repo(tmp_path_factory, remote_repo):
    """Cloned working copy of remote_repo, clean and on main."""
    local = tmp_path_factory.mktemp("local")
    _git(["clone", str(remote_repo), str(local)], cwd=tmp_path_factory.getbasetemp())
    return local


class TestGitSyncHappyPath:
    def test_syncs_main_branch(self, local_repo):
        result = _run_sync(local_repo)
        assert result.returncode == 0, result.stderr
        assert "SYNCED:" in result.stdout
        assert "main" in result.stdout

    def test_output_contains_short_sha(self, local_repo):
        result = _run_sync(local_repo)
        assert result.returncode == 0
        # SYNCED: main (abc1234)
        assert "(" in result.stdout and ")" in result.stdout


class TestGitSyncBranchPriority:
    def test_prefers_release_over_main(self, tmp_path_factory, remote_repo, local_repo):
        """When both release and main exist on origin, release should be chosen."""
        # Push a release branch to the remote
        work = tmp_path_factory.mktemp("work2")
        _git(["clone", str(remote_repo), str(work)], cwd=tmp_path_factory.getbasetemp())
        _git(["checkout", "-b", "release"], cwd=work)
        (work / "RELEASE.md").write_text("release")
        _git(["add", "."], cwd=work)
        _git(["commit", "-m", "release branch"], cwd=work)
        _git(["push", "origin", "release"], cwd=work)

        result = _run_sync(local_repo)
        assert result.returncode == 0, result.stderr
        assert "release" in result.stdout

    def test_falls_back_to_master(self, tmp_path_factory):
        """When only master exists on origin (no main/release), master is used."""
        remote = tmp_path_factory.mktemp("remote_master")
        _git(["init", "--bare", str(remote)], cwd=tmp_path_factory.getbasetemp())
        _git(["symbolic-ref", "HEAD", "refs/heads/master"], cwd=remote)
        work = tmp_path_factory.mktemp("work_master")
        _git(["init", "-b", "master", str(work)], cwd=tmp_path_factory.getbasetemp())
        _git(["remote", "add", "origin", str(remote)], cwd=work)
        (work / "README.md").write_text("master repo")
        _git(["add", "."], cwd=work)
        _git(["commit", "-m", "init master"], cwd=work)
        _git(["push", "origin", "master"], cwd=work)

        local = tmp_path_factory.mktemp("local_master")
        _git(["clone", str(remote), str(local)], cwd=tmp_path_factory.getbasetemp())

        result = _run_sync(local)
        assert result.returncode == 0, result.stderr
        assert "master" in result.stdout


class TestGitSyncErrorCases:
    def test_detached_head_exits_nonzero(self, local_repo):
        """Detached HEAD should fail with a clear error message."""
        # Get current commit SHA to detach at
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(local_repo), env=_GIT_ENV
        ).decode().strip()
        _git(["checkout", sha], cwd=local_repo)

        result = _run_sync(local_repo)
        assert result.returncode != 0
        assert "detached head" in result.stdout.lower() or "detached head" in result.stderr.lower()

    def test_dirty_working_tree_exits_nonzero(self, local_repo):
        """Uncommitted changes should block sync."""
        (local_repo / "dirty.txt").write_text("uncommitted")
        _git(["add", "dirty.txt"], cwd=local_repo)

        result = _run_sync(local_repo)
        assert result.returncode != 0
        assert "uncommitted" in result.stdout.lower() or "uncommitted" in result.stderr.lower()

    def test_dirty_unstaged_file_exits_nonzero(self, local_repo):
        """Unstaged modifications should also block sync."""
        (local_repo / "README.md").write_text("modified")

        result = _run_sync(local_repo)
        assert result.returncode != 0
        msg = (result.stdout + result.stderr).lower()
        assert "uncommitted" in msg or "would be overwritten" in msg

    def test_missing_remote_exits_nonzero(self, local_repo):
        """No 'origin' remote should fail with a clear error."""
        _git(["remote", "remove", "origin"], cwd=local_repo)

        result = _run_sync(local_repo)
        assert result.returncode != 0
        assert "origin" in result.stdout.lower() or "origin" in result.stderr.lower()

    def test_missing_remote_fix_hint(self, local_repo):
        """Error message should include the 'git remote add origin' fix hint."""
        _git(["remote", "remove", "origin"], cwd=local_repo)

        result = _run_sync(local_repo)
        combined = result.stdout + result.stderr
        assert "git remote add origin" in combined

    def test_shallow_clone_syncs_successfully(self, tmp_path_factory, remote_repo):
        """Shallow clones should unshallow (or warn) and still sync successfully."""
        local = tmp_path_factory.mktemp("shallow")
        subprocess.run(
            ["git", "clone", "--depth=1", str(remote_repo), str(local)],
            check=True, capture_output=True, env=_GIT_ENV,
        )
        result = _run_sync(local)
        # Should either succeed (unshallow worked) or succeed with a warning
        assert result.returncode == 0, result.stderr
        assert "SYNCED:" in result.stdout

    def test_no_valid_branch_exits_nonzero(self, tmp_path_factory):
        """When origin has no release/main/master, script should fail."""
        remote = tmp_path_factory.mktemp("remote_other")
        _git(["init", "--bare", str(remote)], cwd=tmp_path_factory.getbasetemp())
        _git(["symbolic-ref", "HEAD", "refs/heads/develop"], cwd=remote)
        work = tmp_path_factory.mktemp("work_other")
        _git(["init", "-b", "develop", str(work)], cwd=tmp_path_factory.getbasetemp())
        _git(["remote", "add", "origin", str(remote)], cwd=work)
        (work / "README.md").write_text("develop")
        _git(["add", "."], cwd=work)
        _git(["commit", "-m", "init develop"], cwd=work)
        _git(["push", "origin", "develop"], cwd=work)

        local = tmp_path_factory.mktemp("local_other")
        _git(["clone", str(remote), str(local)], cwd=tmp_path_factory.getbasetemp())

        result = _run_sync(local)
        assert result.returncode != 0
        assert "no release/main/master" in result.stdout.lower() or \
               "no release/main/master" in result.stderr.lower()
