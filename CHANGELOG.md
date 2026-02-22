# Changelog

All notable changes to repo-indexer are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Initial pre-release. Everything before 1.0.0 is experimental and subject to breaking changes.
> 1.0.0 is reserved for the MVP milestone.

---

## [Unreleased]

---

## [0.0.2] - 2026-02-21

### Added
- Gradle multi-project detection (`settings.gradle`, `settings.gradle.kts` → monorepo)
- Bazel workspace detection (`WORKSPACE`, `MODULE.bazel`, `BUILD` files → monorepo)
- Go workspace detection (`go.work` → monorepo)
- `setup.cfg` as library indicator (flat-layout Python packages now detected correctly)
- Shallow clone handling in `git-sync.sh` (`git fetch --unshallow` with graceful fallback)
- Code/prose token estimation modes in `estimate-tokens.py` (`mode` parameter, `_guess_content_mode()`)
- Repo-type-specific CLAUDE.md templates: monorepo, library, microservices variants
- `TestBuildSystemDetection` test class (9 new tests)

### Fixed
- Flat-layout Python library detection: `setup.cfg` now recognized alongside `pyproject.toml`/`setup.py`
- `git-sync.sh` missing-remote error now shows available remotes and `git remote add origin` fix hint
- `git-sync.sh` fetch failure error now includes remote URL and raw error output

---

## [0.0.1] - 2026-02-20

### Added
- 6-phase indexing workflow (git sync, type detection, analysis, output, validation, memory update)
- Tiered memory architecture: L0 native memory, L1 CLAUDE.md, L2 on-demand files, L3 conversation history
- `detect-repo-type.py` — auto-classifies repos as monorepo, microservices, single_app, or library
- `estimate-tokens.py` — validates token budgets with hard limit enforcement (CLAUDE.md < 500 tokens)
- `generate-memory-update.py` — generates native memory update suggestions after indexing
- `git-sync.sh` — deterministic branch sync (release > main > master priority)
- Reference docs: memory strategy, repo type patterns, document templates, troubleshooting guide
- Plugin manifest and self-hosted marketplace catalog
- `.gitignore`: firebase-debug.log, *.log, SESSION_SUMMARY.md
- `CHANGELOG.md`: [Unreleased] section

### Fixed
- git-sync.sh: POSIX shebang, dirty-tree guard, detached HEAD/rebase/merge checks, remote validation
- detect-repo-type.py: specific exception handling, depth-limited Dockerfile search, compose file variants
- generate-memory-update.py: JSON error handling, missing-key validation, extra-key filtering, Python 3.8 compat
- estimate-tokens.py: UTF-8 encoding safety, memory file budget enforcement
- troubleshooting.md: corrected script reference (validate-structure.py → estimate-tokens.py)
- README.md: clarified script path locations
- marketplace.json: fixed name consistency

### Changed
- SKILL.md: third-person description, added allowed-tools/argument-hint, progress checklist, user confirmation steps, validation feedback loop
- plugin.json: third-person description
- templates.md: added table of contents, fixed nested code fences
