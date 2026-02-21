## What

<!-- Brief description of what this PR does -->

## Why

<!-- Why is this change needed? What problem does it solve? -->

## How

<!-- How does it work? Key implementation decisions? -->

## Testing

- [ ] `pytest tests/ -v` passes
- [ ] Manually tested against a real repo
- [ ] Edge cases considered (empty repo, no git remote, non-existent paths)

## Contribution checklist

- [ ] No external dependencies added (stdlib-only runtime)
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] Shell scripts are POSIX-compatible (`set -e`, no bashisms)
- [ ] Python 3.9+ compatible (no match statements, no 3.10+ type hints)
