"""Test utilities for loading scripts with hyphens in their filenames."""

import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "repo-indexer" / "scripts"


def import_script(name: str) -> ModuleType:
    """Load a script file whose name contains hyphens (not valid Python identifiers)."""
    path = SCRIPTS_DIR / f"{name}.py"
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {path}")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(
            f"Could not load module spec for: {path} — "
            "verify the file exists and is a valid Python script"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
