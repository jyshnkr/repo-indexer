#!/usr/bin/env python3
"""Estimate token count and enforce budgets for .claude/ files."""

import sys
from pathlib import Path

# Rough estimate: 1 token ≈ 4 UTF-8 bytes (more accurate than char count for non-ASCII)
CHARS_PER_TOKEN = 4

# Aggregate budget for all L2 memory files combined
L2_TOTAL_BUDGET = 10_000

BUDGETS = {
    "CLAUDE.md": 500,
    "architecture.md": 5000,
    "conventions.md": 3000,
    "glossary.md": 2000,
}

# Default budget applied to any memory file not listed above
MEMORY_DEFAULT_BUDGET = 5000


def estimate_tokens(text: str) -> int:
    """Convert UTF-8 byte length to an approximate token count."""
    return len(text.encode("utf-8")) // CHARS_PER_TOKEN


# Skip files larger than this to avoid reading multi-GB files into memory
_MAX_FILE_BYTES = 1_000_000  # 1 MB


def check_file(filepath: Path) -> dict:
    """Check a memory file's token count against its budget."""
    if not filepath.exists():
        return {"exists": False}
    if filepath.stat().st_size > _MAX_FILE_BYTES:
        return {"exists": True, "error": "file too large to check", "tokens": 0,
                "budget": BUDGETS.get(filepath.name, MEMORY_DEFAULT_BUDGET), "over": True, "pct": None}
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
            if info.get("error"):
                result["errors"].append(f"CLAUDE.md: {info['error']}")
            else:
                result["errors"].append(f"CLAUDE.md: {info['tokens']} > {info['budget']}")
            result["valid"] = False

    # Check memory files — budget violations are enforced here too
    memory = path / ".claude" / "memory"
    if memory.exists():
        memory_total = 0
        for f in memory.glob("*.md"):
            info = check_file(f)
            result["files"][f"memory/{f.name}"] = info
            file_tokens = info.get("tokens", 0)
            result["total"] += file_tokens
            memory_total += file_tokens
            if info.get("over"):
                if info.get("error"):
                    result["errors"].append(f"memory/{f.name}: {info['error']}")
                else:
                    result["errors"].append(f"memory/{f.name}: {info['tokens']} > {info['budget']}")
                result["valid"] = False
        # Enforce aggregate L2 budget
        if memory_total > L2_TOTAL_BUDGET:
            result["errors"].append(f"L2 total: {memory_total} > {L2_TOTAL_BUDGET} aggregate budget")
            result["valid"] = False

    return result


if __name__ == "__main__":
    root_path = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root_path.is_dir():
        print(f"ERROR: '{root_path}' is not a valid directory", file=sys.stderr)
        sys.exit(1)
    r = validate(str(root_path))
    print(f"Valid: {r['valid']} | Total: {r['total']} tokens")
    for name, info in r["files"].items():
        s = "⚠️ OVER" if info.get("over") else "✓"
        pct = info.get('pct')
        pct_str = f"{pct}%" if pct is not None else "N/A"
        print(f"  {s} {name}: {info.get('tokens',0)}/{info.get('budget','?')} ({pct_str})")
    for e in r["errors"]:
        print(f"❌ {e}")
    sys.exit(0 if r["valid"] else 1)
