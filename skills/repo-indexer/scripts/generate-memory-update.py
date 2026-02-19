#!/usr/bin/env python3
"""Generate Claude native memory update suggestions after indexing."""

from __future__ import annotations

import json
import sys
from datetime import date

REQUIRED_KEYS = {"repo_name", "repo_type", "tech_stack", "key_modules", "patterns"}


def generate_memory_update(
    repo_name: str,
    repo_type: str,
    tech_stack: list[str],
    key_modules: list[str],
    patterns: list[str],
    summary: str = ""
) -> str:
    """Generate memory update text for Claude's native memory."""

    today = date.today().isoformat()

    # Build concise memory entries
    entries = []

    # Core repo info (always include)
    stack_str = ", ".join(tech_stack[:5])  # Limit to top 5
    entries.append(f"Repo: {repo_name} | Type: {repo_type} | Stack: {stack_str}")

    # Index status
    modules_str = ", ".join(key_modules[:4])  # Limit to top 4
    entries.append(f"{repo_name} indexed {today} | Key: {modules_str}")

    # Patterns (if significant)
    if patterns:
        patterns_str = ", ".join(patterns[:3])  # Limit to top 3
        entries.append(f"{repo_name} patterns: {patterns_str}")

    entries_text = "\n".join(entries)

    output = f"""
## Claude Memory Update

After indexing, suggest adding to Claude's memory:

```
{entries_text}
```

### How to add:
1. Ask Claude: "Remember that I work on {repo_name}"
2. Or use memory tool: add the entries above

### Why this matters:
- Next session, Claude already knows this repo exists
- No need to load CLAUDE.md for basic context
- Enables cross-repo pattern recognition
"""
    return output.strip()


if __name__ == "__main__":
    # Example usage / CLI interface
    if len(sys.argv) > 1:
        # Accept JSON input
        try:
            data = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
            print("Usage: generate-memory-update.py '<json>'", file=sys.stderr)
            print("  JSON must contain: repo_name, repo_type, tech_stack, key_modules, patterns", file=sys.stderr)
            sys.exit(1)
        if not isinstance(data, dict):
            print("ERROR: JSON input must be an object, not an array or primitive", file=sys.stderr)
            sys.exit(1)
        missing = REQUIRED_KEYS - data.keys()
        if missing:
            print(f"ERROR: Missing required keys: {', '.join(sorted(missing))}", file=sys.stderr)
            print("  JSON must contain: repo_name, repo_type, tech_stack, key_modules, patterns", file=sys.stderr)
            sys.exit(1)
        # Type validation
        for str_key in ("repo_name", "repo_type"):
            if not isinstance(data.get(str_key), str):
                print(f"ERROR: '{str_key}' must be a string", file=sys.stderr)
                sys.exit(1)
        for list_key in ("tech_stack", "key_modules", "patterns"):
            if not isinstance(data.get(list_key), list):
                print(f"ERROR: '{list_key}' must be an array", file=sys.stderr)
                sys.exit(1)
        ACCEPTED_KEYS = REQUIRED_KEYS | {"summary"}
        filtered = {k: v for k, v in data.items() if k in ACCEPTED_KEYS}
        print(generate_memory_update(**filtered))
    else:
        # Demo output
        print(generate_memory_update(
            repo_name="api-gateway",
            repo_type="microservices",
            tech_stack=["Go 1.21", "gRPC", "PostgreSQL", "Redis"],
            key_modules=["handlers", "services", "middleware", "proto"],
            patterns=["Clean Architecture", "Repository Pattern", "CQRS"]
        ))
