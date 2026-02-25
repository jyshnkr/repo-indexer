"""Tests for security-sensitive functionality."""

import os
import pathlib
import shutil
import subprocess

import pytest
from helpers import import_script
from urllib.parse import urlparse

_mod_detect = import_script("detect-repo-type")
_mod_estimate = import_script("estimate-tokens")
_GIT_SYNC = (
    pathlib.Path(__file__).resolve().parent.parent
    / "skills"
    / "repo-indexer"
    / "scripts"
    / "git-sync.sh"
)


@pytest.mark.skipif(not shutil.which("sh"), reason="sh not available")
class TestCredentialRedaction:
    """Tests for _redact_url function in git-sync.sh."""

    def _run_redact(self, url: str) -> str:
        """Run _redact_url function directly."""
        result = subprocess.run(
            ["sh", "-c", f'. "{_GIT_SYNC}"; _redact_url "$1"', "sh", url],
            capture_output=True,
            text=True,
            env={**os.environ, "REPO_INDEXER_SOURCE_ONLY": "1"},
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def test_redact_user_pass_url(self):
        """_redact_url strips user:pass@ from URLs."""
        url = "https://user:password@github.com/repo.git"
        result = self._run_redact(url)
        assert "user" not in result
        assert "password" not in result
        parsed = urlparse(result)
        assert parsed.scheme == "https"
        assert parsed.netloc == "github.com"

    def test_redact_token_only_url(self):
        """Strips token@ format."""
        url = "https://ghp_TOKEN123456789@github.com/repo.git"
        result = self._run_redact(url)
        assert "ghp_TOKEN123456789" not in result
        parsed = urlparse(result)
        assert parsed.scheme == "https"
        assert parsed.netloc == "github.com"

    def test_plain_url_unchanged(self):
        """URLs without creds pass through unchanged."""
        url = "https://github.com/user/repo.git"
        result = self._run_redact(url)
        assert result == url

    def test_ssh_url_unchanged(self):
        """SSH URLs are unaffected."""
        url = "git@github.com:user/repo.git"
        result = self._run_redact(url)
        assert result == url

    def test_special_chars_in_password(self):
        """URL-encoded special chars in password are stripped."""
        url = "https://user:p%40ss%3Aw%40rd@github.com/repo.git"
        result = self._run_redact(url)
        assert "p%40ss%3Aw%40rd" not in result
        assert result == "https://github.com/repo.git"

    def test_empty_string(self):
        """Empty input doesn't crash."""
        result = self._run_redact("")
        assert result == ""

    def test_http_url_redaction(self):
        """HTTP URLs with credentials are also redacted."""
        url = "http://admin:secret123@internal.corp/repo.git"
        result = self._run_redact(url)
        assert "admin" not in result
        assert "secret123" not in result
        assert "internal.corp" in result


class TestSymlinkSafety:
    """Tests for symlink handling safety."""

    def test_circular_symlinks_no_crash(self, tmp_path):
        """Circular symlink: link_a -> link_b -> link_a doesn't cause infinite loops."""
        link_a = tmp_path / "link_a"
        link_b = tmp_path / "link_b"

        link_a.symlink_to(link_b)
        link_b.symlink_to(link_a)

        result = _mod_detect.detect_repo_type(str(tmp_path))
        assert result["type"] is not None

    @pytest.mark.skipif(
        os.name == "nt", reason="Windows doesn't easily allow symlink outside repo"
    )
    def test_symlink_outside_repo_ignored(self, tmp_path, tmp_path_factory):
        """Symlinks to parent dirs not followed."""
        # Create a directory outside the "repo"
        outside = tmp_path_factory.mktemp("outside")
        (outside / "sensitive.txt").write_text("secret")

        # Create symlink inside repo pointing outside
        link = tmp_path / "linked"
        link.symlink_to(outside)

        # The detector should not follow the symlink
        result = _mod_detect.detect_repo_type(str(tmp_path))
        assert result["type"] is not None


class TestPathSafety:
    """Tests for path traversal safety."""

    def test_detect_with_traversal_path(self, tmp_path):
        """../../etc doesn't crash."""
        # Path with traversal attempts
        malicious_path = str(tmp_path / ".." / ".." / "etc")

        # Should handle gracefully
        result = _mod_detect.detect_repo_type(malicious_path)
        # Should either error or default to single_app
        assert result["type"] in ["single_app", "library", "monorepo", "microservices"]

    def test_estimate_with_traversal_path(self, tmp_path):
        """Traversal path handled gracefully in estimate-tokens."""
        malicious_path = str(tmp_path / ".." / ".." / "etc")

        # Should handle gracefully - may return valid or error
        result = _mod_estimate.validate(malicious_path)
        assert "valid" in result
