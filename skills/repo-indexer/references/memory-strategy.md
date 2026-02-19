# Memory Strategy

## Tiered Architecture

```
L0: CLAUDE NATIVE MEMORY     → Auto-injected, ~100-300 tokens
L1: CLAUDE.md                → Auto-loaded, HARD LIMIT <500 tokens  
L2: .claude/memory/*.md      → On-demand via explicit file reads
L3: CONVERSATION HISTORY     → Searchable, 0 cost until retrieved
```

## L0: Native Memory

**What to store:**
- Repo roster: `"Repo: api-gateway | Type: microservices | Stack: Go, gRPC"`
- Index status: `"api-gateway indexed 2025-02-10"`
- Cross-repo patterns: `"Team uses DDD, clean architecture"`

**Template:**
```
Repo: {name} | Type: {type} | Stack: {stack}
{name} indexed {date} | Key: {modules}
{name} patterns: {patterns}
```

## L1: CLAUDE.md (<500 tokens)

**Must contain ONLY:**
- One-sentence summary
- Tech stack (list, no explanations)
- 4 commands: install, run, test, build
- Context loading instructions

**Template:**
```markdown
# {repo-name}
{One sentence: what + who + why}

## Stack
{lang}, {framework}, {db}, {key-deps}

## Commands
{install} | {run} | {test} | {build}

## Context
1. Check Claude memory for prior knowledge
2. Search past chats: "{repo-name} architecture"  
3. Load .claude/memory/{x}.md only when needed
```

## L2: On-Demand Files

| Task | Load |
|------|------|
| Architecture decisions | `.claude/memory/architecture.md` |
| Code style questions | `.claude/memory/conventions.md` |
| Unknown domain terms | `.claude/memory/glossary.md` |

## L3: Conversation History

**Indexing output format (searchable):**
```markdown
### REPO: {name}
### INDEXED: {date}  
### ARCHITECTURE
{analysis}
### SEARCH KEYWORDS
{repo-name} architecture, {patterns}, {tech-stack}
```

## Token Budgets

| Layer | Budget | When Loaded |
|-------|--------|-------------|
| Native Memory | ~100-300 | Always |
| CLAUDE.md | <500 | Session start |
| memory/*.md | <10,000 total | On-demand |
| Past chats | 0 | When searched |
