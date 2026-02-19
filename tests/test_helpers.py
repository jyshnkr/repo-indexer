"""Tests for test helper utilities."""

import pytest
from helpers import import_script


class TestImportScript:
    def test_nonexistent_script_raises(self):
        """B3: import_script should raise FileNotFoundError for missing scripts."""
        with pytest.raises(FileNotFoundError, match="Script not found"):
            import_script("nonexistent-script-name")

    def test_valid_script_loads(self):
        """Sanity check: known scripts still load correctly."""
        mod = import_script("estimate-tokens")
        assert hasattr(mod, "estimate_tokens")
