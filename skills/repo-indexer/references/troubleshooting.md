# Troubleshooting

## Skill Not Triggering

**Symptom:** Skill doesn't load on "index this repo"

**Check:**
1. Skill installed correctly
2. Not in competing skill conflict
3. Try explicit: "Use repo-indexer skill to..."

---

## Git Sync Failures

**Error:** `No release/main/master branch found`

**Fix:** Check remote branches: `git branch -r`

**Error:** `Permission denied`

**Fix:** Check SSH keys or HTTPS credentials

---

## Token Budget Exceeded

**Symptom:** CLAUDE.md > 500 tokens

**Fix:**
1. Run: `python3 scripts/estimate-tokens.py`
2. Move details to `.claude/memory/`
3. Keep only: summary, stack, commands, context-loading

---

## Memory Not Persisting

**Symptom:** Claude doesn't remember repo next session

**Check:**
1. Was native memory update suggested?
2. Did user confirm memory addition?
3. Try: "What repos do you remember me working on?"

**Fix:** Manually add: "Remember I work on {repo-name}, a {type} using {stack}"

---

## Conversation Search Not Finding Context

**Symptom:** `conversation_search` returns nothing useful

**Cause:** Indexing output missing search keywords

**Fix:** Ensure indexing output includes:
```markdown
### SEARCH KEYWORDS
{repo-name}, architecture, {tech-stack}, {patterns}
```

---

## On-Demand Files Not Loading

**Symptom:** Claude doesn't read memory/*.md when needed

**Check:** Verify files exist: `ls .claude/memory/`

**Fix:** Add explicit instruction in CLAUDE.md:
```markdown
## Context Loading
For architecture: `cat .claude/memory/architecture.md`
```

---

## Validation Errors

Run: `python3 scripts/estimate-tokens.py`

| Error | Fix |
|-------|-----|
| CLAUDE.md over budget | Move content to memory/ |
| Missing .claude/memory/ | Create directory |
| Files too large | Split or summarize |
