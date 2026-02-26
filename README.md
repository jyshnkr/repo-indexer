# repo-indexer

**Index any codebase for persistent Claude context — minimal token overhead between sessions (~500 tokens for CLAUDE.md boot).**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.0.5-blue.svg)](.claude-plugin/plugin.json)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-orange.svg)](https://claude.ai/plugins)

---

## The Problem

Every new Claude session starts blank. You re-explain your architecture, your conventions, your stack — burning hundreds of tokens just to get Claude up to speed. For large codebases, this context tax is constant and expensive.

## The Solution

repo-indexer runs a structured 5-phase analysis of your codebase and writes the results into a **tiered memory system** that scales across sessions with near-zero overhead:

```
L0: Claude Native Memory  → repo roster, patterns (~100 tokens, always present)
L1: CLAUDE.md             → boot loader only (<500 tokens, auto-loaded every session)
L2: .claude/memory/*.md   → deep context files (loaded on-demand, only when needed)
L3: Conversation History  → full analysis output (searchable, costs 0 tokens until used)
```

Claude loads L0 + L1 automatically. L2 and L3 are retrieved only when the task demands it. **Files are pointers, not stores.**

---

## Quick Start

```bash
# Install the plugin
/plugin marketplace add jyshnkr/repo-indexer

# Install the skill
/plugin install repo-indexer
```

Then in any project directory:

```
index this repo
```

---

## What It Does

### Phase 1: Detect Repo Type
Automatically classifies the codebase:
- **Monorepo** — `pnpm-workspace.yaml`, `turbo.json`, `packages/`, `apps/`
- **Microservices** — multiple Dockerfiles, `docker-compose` with 3+ services
- **Single App** — default when no strong signals are present
- **Library** — `pyproject.toml`, `Cargo.toml`, `setup.py`, `go.mod`, or `src/`-only layout (no `apps/`)
Heuristic note: a single weak signal may still default to **Single App**.

### Phase 2: Index
Analyzes 9 areas systematically:
1. Config files (package.json, pyproject.toml, Cargo.toml, go.mod)
2. Entry points (main, CLI, server bootstrap)
3. Directory structure (depth 3)
4. Core modules (business logic, services, models)
5. API surface (routes, endpoints, schemas)
6. Data layer (models, migrations, ORM)
7. External dependencies (third-party integrations)
8. Build/deploy (Dockerfile, CI/CD, Makefile)
9. Tests (structure, fixtures, patterns)

### Phase 3: Generate Output
- Full analysis written to **conversation** (L3) with `### SEARCH KEYWORDS` for retrieval
- Minimal `.claude/` file tree created at repo root (L2)
- `CLAUDE.md` created as a <500 token boot loader (L1)

### Phase 4: Validate Token Budgets
```bash
python3 skills/repo-indexer/scripts/estimate-tokens.py
```
Validates budgets using a heuristic token estimate (CLAUDE.md must be under 500 tokens).

### Phase 5: Suggest Native Memory Update
```bash
python3 skills/repo-indexer/scripts/generate-memory-update.py
```
Suggests 2–3 lines to add to Claude's native memory so the next session starts with repo awareness — no CLAUDE.md load required.

---

## Token Budget

| Layer | Budget | When Loaded |
|-------|--------|-------------|
| L0: Native Memory | ~100–300 tokens | Always (free) |
| L1: CLAUDE.md | < 500 tokens | Every session start |
| L2: memory/*.md | < 10,000 tokens total | On-demand only |
| L3: Conversation History | 0 tokens | When searched |

**Total auto-loaded per session: < 800 tokens.** Everything else costs nothing until you need it.
Token counts are estimated via a bytes-per-token heuristic; treat these as guardrails, not exact model counts.

---

## Use Cases

**"Index this repo"**
→ Full 5-phase workflow. Claude knows your project before you ask your first question.

**"Set up Claude context for this project"**
→ Same workflow. Optimized for team onboarding — every developer gets instant Claude context.

**"Help me understand this codebase"**
→ Checks existing Claude memory and past conversations first. If prior indexing found, uses it. If `.claude/` exists, compares with current codebase, flags inconsistencies, updates incrementally.

---

## Output Structure

After indexing, your repo gets:

```
your-project/
├── CLAUDE.md                    # <500 token boot loader (L1)
└── .claude/
    ├── memory/
    │   ├── architecture.md      # System design, diagrams, key flows (L2)
    │   ├── conventions.md       # Naming, patterns, git workflow (L2)
    │   └── glossary.md          # Domain terms, acronyms (L2)
    ├── plans/                   # Empty — user-managed
    └── checkpoints/             # Empty — user-managed
```

The `<!-- USER -->` marker in each file preserves your own notes through re-indexing.

---

## Scripts Reference

All scripts live under `skills/repo-indexer/scripts/`.

| Script | Purpose |
|--------|---------|
| `detect-repo-type.py` | Classify repo as monorepo/microservices/single_app/library |
| `estimate-tokens.py` | Validate token budgets for all `.claude/` files |
| `generate-memory-update.py` | Generate native memory update suggestions |

All scripts use Python stdlib only — no external dependencies.

---

## Supported Repo Types

| Type | Detection Signals |
|------|------------------|
| Monorepo | `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, `packages/` dir |
| Microservices | 3+ `build:` entries in docker-compose, multiple Dockerfiles |
| Single App | Default when no strong signals are present |
| Library | `setup.py`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or `src/`-only layout |

---

## Contributing

Issues and PRs welcome. When opening an issue, please include:
- Your repo type (monorepo/microservices/single_app/library)
- The phase where the problem occurred
- Output from the relevant script

---

## License

MIT — see [LICENSE](LICENSE).
