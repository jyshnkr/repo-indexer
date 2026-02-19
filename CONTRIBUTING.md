# Contributing to repo-indexer

Thank you for your interest in improving repo-indexer!

## How to Contribute

### Reporting Bugs

Open an issue and include:
- Your repo type (monorepo / microservices / single_app / library)
- The phase where the problem occurred (1–6)
- Output from the relevant script (run it manually and paste)
- OS and Python version

### Suggesting Improvements

Open an issue describing:
- The use case you're trying to support
- What the current behavior is
- What you'd like it to do instead

### Submitting Pull Requests

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test against at least one real repo
5. Open a PR with a description of what changed and why

## What to Contribute

Good areas for contribution:

- **New repo type detection patterns** — Add signals to `detect-repo-type.py` for frameworks not yet covered (e.g., Nx workspaces, Gradle multi-project, Bazel)
- **Template improvements** — Better CLAUDE.md or memory/*.md templates in `references/templates.md`
- **Script robustness** — Edge cases in git-sync.sh (shallow clones, no remote, detached HEAD)
- **Token estimation** — Improve the chars-per-token approximation in `estimate-tokens.py`
- **Troubleshooting docs** — Document new failure modes in `references/troubleshooting.md`

## Code Style

- Python scripts: stdlib only, no external dependencies
- Shell scripts: POSIX-compatible, `set -e`, no bashisms unless unavoidable
- All scripts must have a shebang line and be executable

## File Layout

```
.claude-plugin/       Plugin manifest and marketplace catalog
skills/repo-indexer/  The skill itself
  SKILL.md            Skill definition (frontmatter + instructions)
  scripts/            Executable helper scripts
  references/         Reference docs loaded on-demand by the skill
```
