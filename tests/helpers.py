"""Test utilities for loading scripts with hyphens in their filenames."""

import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "repo-indexer" / "scripts"


def import_script(name: str) -> ModuleType:
    """Load a script file whose name contains hyphens (not valid Python identifiers)."""
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module
