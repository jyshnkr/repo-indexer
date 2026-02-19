#!/usr/bin/env python3
"""Estimate token count and enforce budgets for .claude/ files."""

import sys
from pathlib import Path

# Rough estimate: 1 token ≈ 4 chars
CHARS_PER_TOKEN = 4

BUDGETS = {
    "CLAUDE.md": 500,
    "architecture.md": 5000,
    "conventions.md": 3000,
    "glossary.md": 2000,
}

# Default budget applied to any memory file not listed above
MEMORY_DEFAULT_BUDGET = 5000


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def check_file(filepath: Path) -> dict:
    if not filepath.exists():
        return {"exists": False}
    content = filepath.read_text(encoding="utf-8", errors="replace")
    tokens = estimate_tokens(content)
    budget = BUDGETS.get(filepath.name, MEMORY_DEFAULT_BUDGET)
    return {
        "exists": True,
        "tokens": tokens,
        "budget": budget,
        "over": tokens > budget,
        "pct": round(tokens / budget * 100, 1)
    }


def validate(root: str = ".") -> dict:
    path = Path(root)
    result = {"valid": True, "files": {}, "total": 0, "errors": []}

    # Check CLAUDE.md
    claude_md = path / "CLAUDE.md"
    if claude_md.exists():
        info = check_file(claude_md)
        result["files"]["CLAUDE.md"] = info
        result["total"] += info.get("tokens", 0)
        if info.get("over"):
            result["errors"].append(f"CLAUDE.md: {info['tokens']} > {info['budget']}")
            result["valid"] = False

    # Check memory files — budget violations are enforced here too
    memory = path / ".claude" / "memory"
    if memory.exists():
        for f in memory.glob("*.md"):
            info = check_file(f)
            result["files"][f"memory/{f.name}"] = info
            result["total"] += info.get("tokens", 0)
            if info.get("over"):
                result["errors"].append(f"memory/{f.name}: {info['tokens']} > {info['budget']}")
                result["valid"] = False

    return result


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    r = validate(root)
    print(f"Valid: {r['valid']} | Total: {r['total']} tokens")
    for name, info in r["files"].items():
        s = "⚠️ OVER" if info.get("over") else "✓"
        print(f"  {s} {name}: {info.get('tokens',0)}/{info.get('budget','?')} ({info.get('pct',0)}%)")
    for e in r["errors"]:
        print(f"❌ {e}")
    sys.exit(0 if r["valid"] else 1)
