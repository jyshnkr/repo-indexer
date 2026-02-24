"""Chaos/fault injection tests."""

import os
import pytest
from helpers import import_script

_mod_detect = import_script("detect-repo-type")
_mod_estimate = import_script("estimate-tokens")
_mod_generate = import_script("generate-memory-update")


class TestChaos:
    """Fault injection and edge case handling tests."""

    def test_detect_binary_package_json(self, tmp_path):
        """Random bytes in package.json → warns, no crash."""
        (tmp_path / "package.json").write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
        result = _mod_detect.detect_repo_type(str(tmp_path))
        # Should not crash, should return some result
        assert result["type"] is not None

    def test_detect_empty_docker_compose(self, tmp_path):
        """0-byte compose → no crash."""
        (tmp_path / "docker-compose.yml").write_text("")
        result = _mod_detect.detect_repo_type(str(tmp_path))
        # Should not crash
        assert result["type"] is not None

    def test_estimate_empty_claude_md(self, tmp_path):
        """Empty file → 0 tokens, within budget."""
        (tmp_path / "CLAUDE.md").write_text("")
        result = _mod_estimate.validate(str(tmp_path))
        assert result["valid"] is True
        claude_info = result["files"].get("CLAUDE.md", {})
        assert claude_info.get("tokens", -1) == 0

    def test_generate_very_long_repo_name(self):
        """10000-char name → no crash."""
        long_name = "a" * 10000
        result = _mod_generate.generate_memory_update(
            repo_name=long_name,
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
        )
        assert "a" * 10000 in result

    def test_generate_unicode_cjk_input(self):
        """CJK in repo_name → no crash."""
        result = _mod_generate.generate_memory_update(
            repo_name="プロジェクト",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
        )
        assert "プロジェクト" in result

    def test_generate_unicode_emoji_input(self):
        """Emoji in repo_name → no crash."""
        result = _mod_generate.generate_memory_update(
            repo_name="test\U0001F600project",
            repo_type="single_app",
            tech_stack=["Python"],
            key_modules=["m"],
            patterns=[],
        )
        assert "\U0001F600" in result

    @pytest.mark.skipif(not hasattr(os, "getuid") or os.getuid() == 0, reason="Test requires non-root to enforce permissions")
    def test_detect_unreadable_subdir(self, tmp_path):
        """chmod 000 dir → graceful handling (skip on root)."""
        # Create a subdir with a Dockerfile
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "Dockerfile").write_text("FROM python:3\n")
        # Make it unreadable
        subdir.chmod(0o000)

        try:
            result = _mod_detect.detect_repo_type(str(tmp_path))
            # Should not crash, should handle gracefully
            assert result["type"] is not None
        finally:
            subdir.chmod(0o755)

    @pytest.mark.skipif(not hasattr(os, "getuid") or os.getuid() == 0, reason="Test requires non-root to enforce permissions")
    def test_estimate_unreadable_memory_dir(self, tmp_path):
        """chmod 000 → graceful handling (skip on root)."""
        memory = tmp_path / ".claude" / "memory"
        memory.mkdir(parents=True)
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        (memory / "test.md").write_text("content\n")
        # Make memory dir unreadable
        memory.chmod(0o000)

        try:
            result = _mod_estimate.validate(str(tmp_path))
            # Should handle gracefully - CLAUDE.md should still be valid
            assert "CLAUDE.md" in result["files"]
        finally:
            memory.chmod(0o755)

    def test_detect_malformed_json_docker_compose(self, tmp_path):
        """Malformed docker-compose.yml → skip gracefully."""
        (tmp_path / "docker-compose.yml").write_text(
            "services:\n"
            "  api:\n"
            "    build: ./api\n"
            "    ports: [not valid yaml"
        )
        result = _mod_detect.detect_repo_type(str(tmp_path))
        # Should not crash, should return result
        assert result["type"] is not None
