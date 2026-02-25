---
name: repo-indexer
description: Indexes and documents a codebase for persistent Claude context with minimal token overhead. Use when asked to index a repo, understand a codebase, create CLAUDE.md, set up Claude memory, bootstrap context, onboard to a project, or document codebase for Claude. Triggers on phrases like "index this repo", "understand this codebase", "set up context", "create project memory", "help me onboard". Creates tiered memory system using Claude native memory + minimal boot files + on-demand loading + conversation history as knowledge store. Do NOT use for general code questions, debugging, or tasks unrelated to codebase indexing/documentation.
allowed-tools: Bash, Read, Write, Glob, Grep
argument-hint: [path]
license: MIT
metadata:
  version: 0.0.4
  author: JayaShankar Mangina
---

# Repo Indexer

Indexes codebases with minimal context window overhead using tiered memory.

## Getting Started

**Prerequisites:** Python 3.9+. Run from the project root directory.

## Memory Architecture

```
L0: Claude Native Memory  → repo roster, patterns (~100 tokens, auto)
L1: CLAUDE.md             → boot loader only (<500 tokens, auto-load)
L2: .claude/memory/*.md   → deep context (on-demand, explicit load)
L3: Conversation History  → full analysis (searchable, 0 cost until used)
```

**Token budgets:** Native Memory ~100–300 | CLAUDE.md <500 | memory/*.md <10,000 total | Past chats: 0 until searched

**L2 file loading guide:** Architecture decisions → `architecture.md` | Code style → `conventions.md` | Unknown terms → `glossary.md`

## Task Progress

Use TodoWrite to track each phase dynamically:
- Phase 1: Detect repo type
- Phase 2: Analyze codebase (9 areas)
- Phase 3: Generate output files
- Phase 4: Validate token budgets
- Phase 5: Suggest memory update

## Workflow

### Phase 1: Detect Repo Type

```bash
python3 scripts/detect-repo-type.py "$ARGUMENTS"
```

### Phase 2: Index

Analyze systematically:
1. **Config**: package.json, pyproject.toml, Cargo.toml, go.mod
2. **Entry points**: main files, CLI, server bootstrap
3. **Structure**: directory layout to depth 3
4. **Core modules**: business logic, services, models
5. **API surface**: routes, endpoints, schemas
6. **Data layer**: models, migrations, ORM
7. **External deps**: third-party integrations
8. **Build/deploy**: Dockerfile, CI/CD, Makefile
9. **Tests**: structure, fixtures, patterns

Before generating files, present the proposed `.claude/` structure to the user for confirmation.

### Phase 3: Generate Output

**Output to conversation (L3):**

Full analysis using format in `references/templates.md` → "Indexing Output Format". Include `### SEARCH KEYWORDS` for retrieval.

**Select CLAUDE.md template by repo type:**

Use the type-specific variant from `references/templates.md`:
- **Monorepo** → "CLAUDE.md — Monorepo variant" (packages list, workspace commands)
- **Library** → "CLAUDE.md — Library variant" (public API section, publish commands)
- **Microservices** → "CLAUDE.md — Microservices variant" (services table, compose commands)
- **Single App** → base "CLAUDE.md" template

**Create files:**

```
.claude/
├── memory/
│   ├── architecture.md   # From references/templates.md
│   ├── conventions.md
│   └── glossary.md
├── plans/                # Empty, user-managed
└── checkpoints/          # Empty, user-managed

CLAUDE.md                 # At repo root, <500 tokens
```

### Phase 4: Validate

```bash
python3 scripts/estimate-tokens.py
```

Must pass: CLAUDE.md < 500 tokens, all memory files within budget.

If validation fails:
1. Move content from CLAUDE.md to `.claude/memory/` files
2. Re-run `scripts/estimate-tokens.py`
3. Repeat until all files pass their budget

### Phase 5: Memory Update

```bash
python3 scripts/generate-memory-update.py
```

Suggest user add to Claude's native memory:
```
Repo: {name} | Type: {type} | Stack: {stack}
{name} indexed {date} | Key: {modules}
```

## Examples

**User:** "Index this repo"
1. Run detect-repo-type.py (Phase 1)
2. Analyze all 9 areas (Phase 2)
3. Output full analysis to conversation + create .claude/ structure (Phase 3)
4. Validate token budgets (Phase 4)
5. Suggest native memory update (Phase 5)

**User:** "Help me understand this codebase"
1. Check Claude memory for prior indexing
2. Search past chats: "{repo-name} architecture"
3. If not found: run full indexing workflow

## If .claude/ Exists

1. Load existing files
2. Compare with current codebase
3. Flag inconsistencies
4. Update incrementally
5. Preserve `<!-- USER -->` sections

## Error Handling

Common issues:
- Python version error → requires Python 3.9+: `python3 --version` or `which python3`

## Critical Rules

- CLAUDE.md hard limit: **500 tokens**
- Full analysis goes in **conversation**, not files
- Files are **pointers**, not stores
- Always suggest **native memory update**
- Include **search keywords** in output
