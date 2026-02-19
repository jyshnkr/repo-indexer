#!/usr/bin/env python3
"""Generate Claude native memory update suggestions after indexing."""

import json
import sys
from datetime import date

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
    
    output = f"""
## Claude Memory Update

After indexing, suggest adding to Claude's memory:

```
{chr(10).join(entries)}
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
        data = json.loads(sys.argv[1])
        print(generate_memory_update(**data))
    else:
        # Demo output
        print(generate_memory_update(
            repo_name="api-gateway",
            repo_type="microservices",
            tech_stack=["Go 1.21", "gRPC", "PostgreSQL", "Redis"],
            key_modules=["handlers", "services", "middleware", "proto"],
            patterns=["Clean Architecture", "Repository Pattern", "CQRS"]
        ))
