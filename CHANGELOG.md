# Changelog

All notable changes to repo-indexer are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.0] - 2026-02-18

### Added
- 6-phase indexing workflow (git sync, type detection, analysis, output, validation, memory update)
- Tiered memory architecture: L0 native memory, L1 CLAUDE.md, L2 on-demand files, L3 conversation history
- `detect-repo-type.py` — auto-classifies repos as monorepo, microservices, single_app, or library
- `estimate-tokens.py` — validates token budgets with hard limit enforcement (CLAUDE.md < 500 tokens)
- `generate-memory-update.py` — generates native memory update suggestions after indexing
- `git-sync.sh` — deterministic branch sync (release > main > master priority)
- Reference docs: memory strategy, repo type patterns, document templates, troubleshooting guide
- Plugin manifest and self-hosted marketplace catalog
