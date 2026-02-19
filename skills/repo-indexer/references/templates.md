# Document Templates

## Contents

- [CLAUDE.md](#claudemd-500-tokens)
- [architecture.md](#architecturemd)
- [conventions.md](#conventionsmd)
- [glossary.md](#glossarymd)
- [Indexing Output Format](#indexing-output-format-for-conversation-history)

---

## CLAUDE.md (<500 tokens)

```markdown
# {repo-name}
{One sentence: purpose, users, core value}

## Stack
{lang} {version}, {framework}, {db}, {key-dep-1}, {key-dep-2}

## Commands
```bash
# Install
{install_cmd}

# Run  
{run_cmd}

# Test
{test_cmd}

# Build
{build_cmd}
```

## Context Loading
1. Claude memory has repo overview
2. Search past chats: "{repo-name} architecture"
3. If needed: `cat .claude/memory/{file}.md`

<!-- USER: Add notes below -->
```

---

## architecture.md

```markdown
# Architecture

## Overview
{2-3 sentences: architectural style, key decisions}

## Diagram
```mermaid
graph TB
    subgraph External
        Client[Client]
    end
    subgraph App
        API[API Layer]
        SVC[Service Layer]
        DATA[Data Layer]
    end
    Client --> API --> SVC --> DATA
```

## Boundaries

| Component | Owns | Depends On |
|-----------|------|------------|
| {component} | {data} | {deps} |

## Key Flows
1. {flow-name}: {step} → {step} → {step}

<!-- USER -->
```

---

## conventions.md

```markdown
# Conventions

## Naming
| Element | Pattern | Example |
|---------|---------|---------|
| Files | {pattern} | `{example}` |
| Functions | {pattern} | `{example}` |

## Patterns
- Error handling: {pattern}
- Logging: {pattern}
- Testing: {location}, {naming}

## Git
- Branches: `{pattern}`
- Commits: `{pattern}`

<!-- USER -->
```

---

## glossary.md

```markdown
# Glossary

## Domain Terms
| Term | Definition |
|------|------------|
| {term} | {definition} |

## Acronyms
| Acronym | Meaning |
|---------|---------|
| {acronym} | {meaning} |

<!-- USER -->
```

---

## Indexing Output Format (for conversation history)

```markdown
---
### REPO: {name}
### INDEXED: {YYYY-MM-DD}
### TYPE: {monorepo|microservices|single_app|library}

### SUMMARY
{2-3 sentence overview}

### TECH STACK
- Language: {lang} {version}
- Framework: {framework}
- Database: {db}
- Key deps: {deps}

### ARCHITECTURE
{Detailed analysis - this lives in conversation, not files}

### CONVENTIONS
{Detailed analysis}

### KEY INSIGHTS
- {insight-1}
- {insight-2}

### SEARCH KEYWORDS
{repo-name}, {tech-stack}, {patterns}, {domain-terms}
---
```

This format enables effective `conversation_search` retrieval.
