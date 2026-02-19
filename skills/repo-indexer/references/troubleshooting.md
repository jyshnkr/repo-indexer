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

---

## Script Permission Errors

**Error:** `Permission denied` when running scripts

**Fix:**
```bash
chmod +x skills/repo-indexer/scripts/git-sync.sh
chmod +x skills/repo-indexer/scripts/*.py
```

Or invoke Python explicitly:
```bash
python3 skills/repo-indexer/scripts/detect-repo-type.py .
```

---

## Python Version Requirements

**Error:** `SyntaxError` or unexpected behavior from scripts

**Cause:** Scripts require Python 3.9+

**Check:** `python3 --version`

**Fix:** Install Python 3.9+ from [python.org](https://www.python.org/downloads/) or via your package manager:
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11
```

---

## Re-indexing After Repo Changes

**Symptom:** `.claude/` files are stale after major refactors or new features

**Fix:**
1. Run the full indexing workflow again: `index this repo`
2. The skill detects existing `.claude/` and updates incrementally
3. Sections marked `<!-- USER -->` are preserved during re-indexing
4. After updating, re-run token validation: `python3 scripts/estimate-tokens.py`
