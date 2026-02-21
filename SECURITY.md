# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x.y (current) | Yes |

Only the latest release receives security fixes.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/jyshnkr/repo-indexer/security/advisories/new).

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You'll receive a response within 7 days. If confirmed, a patch will be released as soon as possible with credit to the reporter (unless you prefer to remain anonymous).

## Scope

repo-indexer is a local Claude Code plugin. It:

- Reads files from your local filesystem
- Runs `git` commands against your local repository
- Does **not** make network requests beyond `git fetch/pull`
- Does **not** transmit code or file contents to external services

Security issues of interest:
- Path traversal in script arguments
- Shell injection via repository metadata (branch names, commit messages)
- Unsafe file reads that could expose credentials

Out of scope:
- Issues requiring physical access to the machine
- Vulnerabilities in Claude Code itself (report to Anthropic)
- Issues in `git` (report to the Git project)
