#!/usr/bin/env python3
"""Detect repository architecture type."""

import json
import os
import sys
from pathlib import Path

# Directories to skip during filesystem traversal
_SKIP_DIRS = {".git", "node_modules", "vendor", "venv", ".venv", "__pycache__"}

# Scoring constants
# Directory markers score lower than config files — a bare "packages/" dir is weak evidence.
_MONOREPO_DIR_SCORE = 2
_MONOREPO_CONFIG_SCORE = 3
# Minimum services in docker-compose to count as microservices signal.
MIN_SERVICES_FOR_MICROSERVICES = 3
# Maximum directory depth to traverse when searching for Dockerfiles.
MAX_DOCKERFILE_DEPTH = 4
# Abort traversal after visiting this many directories (breadth guard for huge trees).
MAX_DIRS_VISITED = 1000


def _find_dockerfiles(root: Path, max_depth: int = MAX_DOCKERFILE_DEPTH) -> list[str]:
    """Find Dockerfiles up to max_depth levels deep, skipping common noise dirs.

    Symlinks are not followed (followlinks=False) to prevent path traversal
    outside the repository root. Traversal aborts after MAX_DIRS_VISITED
    directories to avoid excessive I/O on very wide trees.
    """
    found = []
    dirs_visited = 0
    root_resolved = root.resolve()
    root_str = str(root_resolved)
    for dirpath, dirnames, filenames in os.walk(root_str, followlinks=False):
        dirs_visited += 1
        if dirs_visited > MAX_DIRS_VISITED:
            dirnames.clear()  # stop descending
            continue
        # Calculate current depth relative to root
        depth = dirpath[len(root_str):].count(os.sep)
        if depth >= max_depth:
            dirnames.clear()
            continue
        # Prune directories we never want to descend into
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        if "Dockerfile" in filenames:
            found.append(os.path.join(dirpath, "Dockerfile"))
    return found


def detect_repo_type(root: str = ".") -> dict:
    """Analyse repo structure and return the detected architecture type with confidence."""
    path = Path(root)

    indicators = {
        "monorepo": 0,
        "microservices": 0,
        "single_app": 0,
        "library": 0
    }

    evidence = []

    # Check for monorepo indicators
    monorepo_markers = ["packages/", "apps/", "libs/", "modules/", "services/"]
    # Workspace config files score +3 each (stronger signal than a bare directory).
    workspaces_files = ["pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"]

    for marker in monorepo_markers:
        # Directory markers score +2 (weaker: could exist in any project type).
        if (path / marker).is_dir():
            indicators["monorepo"] += _MONOREPO_DIR_SCORE
            evidence.append(f"Found {marker}")

    for wf in workspaces_files:
        # Workspace config files are authoritative signals, hence the higher weight.
        if (path / wf).exists():
            indicators["monorepo"] += _MONOREPO_CONFIG_SCORE
            evidence.append(f"Found {wf}")

    # Check package.json for workspaces field
    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            if "workspaces" in data:
                # Explicit workspaces declaration is a strong monorepo signal.
                indicators["monorepo"] += _MONOREPO_CONFIG_SCORE
                evidence.append("package.json has workspaces")
        except json.JSONDecodeError as exc:
            print(f"WARNING: Could not parse {pkg_json} as JSON: {exc}", file=sys.stderr)
        except OSError as exc:
            print(f"WARNING: Could not read {pkg_json}: {exc}", file=sys.stderr)

    # Check for microservices indicators — try all common compose file names
    compose_files = [
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    ]
    for compose_name in compose_files:
        compose_path = path / compose_name
        if compose_path.exists():
            try:
                content = compose_path.read_text(encoding="utf-8", errors="replace")
                # Count "build:" or "image:" as proxies for service count.
                # Only count lines where the keyword appears before any "#"
                # comment marker. This avoids adding a YAML parser dependency
                # while reducing false positives from commented-out services.
                service_count = 0
                for line in content.splitlines():
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    comment_pos = line.find("#")
                    effective = line if comment_pos == -1 else line[:comment_pos]
                    if "build:" in effective or "image:" in effective:
                        service_count += 1
                if service_count >= MIN_SERVICES_FOR_MICROSERVICES:
                    indicators["microservices"] += service_count
                    evidence.append(f"{compose_name} with {service_count} services")
            except OSError as exc:
                print(f"WARNING: Could not read {compose_name}: {exc}", file=sys.stderr)
                continue  # Try next variant
            break  # Only count the first compose file successfully read

    # Check for multiple Dockerfiles (depth-limited to avoid traversing huge trees)
    dockerfiles = _find_dockerfiles(path)
    if len(dockerfiles) > 2:
        indicators["microservices"] += len(dockerfiles)
        evidence.append(f"{len(dockerfiles)} Dockerfiles found")

    # Check for library indicators
    lib_markers = ["setup.py", "pyproject.toml", "Cargo.toml", "go.mod"]
    src_only = (path / "src").is_dir() and not (path / "apps").is_dir()

    for marker in lib_markers:
        if (path / marker).exists():
            indicators["library"] += 1

    if src_only and not any((path / m).is_dir() for m in monorepo_markers):
        indicators["library"] += 2
        indicators["single_app"] += 2

    # Determine winner
    repo_type = max(indicators, key=lambda k: indicators[k])
    # Confidence = winning score / total score across all categories (0–1 range).
    confidence = indicators[repo_type] / max(sum(indicators.values()), 1)

    # Default to single_app if no strong signals
    if indicators[repo_type] < 2:
        repo_type = "single_app"
        confidence = 0.5
        evidence.append("No strong indicators, defaulting to single_app")

    return {
        "type": repo_type,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "scores": indicators
    }


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"ERROR: '{root}' is not a valid directory", file=sys.stderr)
        sys.exit(1)
    result = detect_repo_type(str(root))
    print(f"TYPE: {result['type']} (confidence: {result['confidence']})")
    for e in result['evidence']:
        print(f"  - {e}")
