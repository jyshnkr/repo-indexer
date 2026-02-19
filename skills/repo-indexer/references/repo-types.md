# Repo Type Patterns

## Detection

Run: `python scripts/detect-repo-type.py`

## Type: Monorepo

**Indicators:** `packages/`, `apps/`, `pnpm-workspace.yaml`, `nx.json`, `turbo.json`

**Indexing approach:**
1. Index root config first (workspace settings)
2. Map package dependencies
3. Index each package as sub-unit
4. Document inter-package relationships

**CLAUDE.md additions:**
```markdown
## Packages
- `packages/core` - Shared utilities
- `packages/api` - Backend service
- `apps/web` - Frontend app

## Package Commands
pnpm -F {package} {command}
```

**Memory note:** Store package roster in native memory

---

## Type: Microservices

**Indicators:** Multiple `Dockerfile`, `docker-compose.yml` with 3+ services, `k8s/` or `helm/`

**Indexing approach:**
1. Map service boundaries
2. Document inter-service communication (REST, gRPC, events)
3. Index shared libraries/protos
4. Document deployment topology

**CLAUDE.md additions:**
```markdown
## Services
- `api-gateway` - Entry point, auth
- `user-service` - User management
- `order-service` - Order processing

## Service Commands
docker-compose up {service}
```

**Memory note:** Store service topology in native memory

---

## Type: Single App

**Indicators:** Single `Dockerfile`, standard `src/` layout, no workspace config

**Indexing approach:**
1. Standard module analysis
2. Focus on internal architecture
3. Document entry points and data flow

**CLAUDE.md additions:**
```markdown
## Structure
src/
├── api/       # HTTP handlers
├── services/  # Business logic
├── models/    # Data structures
└── utils/     # Helpers
```

---

## Type: Library

**Indicators:** `setup.py`, `pyproject.toml`, `Cargo.toml`, `src/` only, no `apps/`

**Indexing approach:**
1. Public API surface
2. Internal modules
3. Test patterns
4. Build/publish workflow

**CLAUDE.md additions:**
```markdown
## Public API
- `lib.parse()` - Main entry
- `lib.Config` - Configuration

## Publish
{publish_command}
```
