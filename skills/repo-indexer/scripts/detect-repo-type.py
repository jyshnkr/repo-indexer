#!/usr/bin/env python3
"""Detect repository architecture type."""

import os
import json
from pathlib import Path

def detect_repo_type(root: str = ".") -> dict:
    root = Path(root)
    
    indicators = {
        "monorepo": 0,
        "microservices": 0,
        "single_app": 0,
        "library": 0
    }
    
    evidence = []
    
    # Check for monorepo indicators
    monorepo_markers = ["packages/", "apps/", "libs/", "modules/", "services/"]
    workspaces_files = ["pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"]
    
    for marker in monorepo_markers:
        if (root / marker).is_dir():
            indicators["monorepo"] += 2
            evidence.append(f"Found {marker}")
    
    for wf in workspaces_files:
        if (root / wf).exists():
            indicators["monorepo"] += 3
            evidence.append(f"Found {wf}")
    
    # Check package.json for workspaces
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            if "workspaces" in data:
                indicators["monorepo"] += 3
                evidence.append("package.json has workspaces")
        except: pass
    
    # Check for microservices indicators
    docker_compose = root / "docker-compose.yml"
    if docker_compose.exists():
        content = docker_compose.read_text()
        service_count = content.count("build:")
        if service_count > 2:
            indicators["microservices"] += service_count
            evidence.append(f"docker-compose with {service_count} services")
    
    # Check for multiple Dockerfiles
    dockerfiles = list(root.rglob("Dockerfile"))
    if len(dockerfiles) > 2:
        indicators["microservices"] += len(dockerfiles)
        evidence.append(f"{len(dockerfiles)} Dockerfiles found")
    
    # Check for library indicators
    lib_markers = ["setup.py", "pyproject.toml", "Cargo.toml", "go.mod"]
    src_only = (root / "src").is_dir() and not (root / "apps").is_dir()
    
    for marker in lib_markers:
        if (root / marker).exists():
            indicators["library"] += 1
    
    if src_only and not any((root / m).is_dir() for m in monorepo_markers):
        indicators["library"] += 2
        indicators["single_app"] += 2
    
    # Determine winner
    repo_type = max(indicators, key=indicators.get)
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
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    result = detect_repo_type(root)
    print(f"TYPE: {result['type']} (confidence: {result['confidence']})")
    for e in result['evidence']:
        print(f"  - {e}")
