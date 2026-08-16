# Experimental Log

This file records engineering experiments, architecture decisions, rejected approaches, benchmarks, design investigations, and engineering observations.

## Entries

### Date: 2026-08-15
**Experiment / Decision:**
Repository Architecture Restructuring

**Context:**
The initial repository structure organized directories by individual team members.

**Problem:**
A production-style GitHub repository should represent software architecture rather than developer ownership.

**Initial approach:**
Developer-specific directories.

**Decision:**
Refactor the repository so physical directories represent system components.

**New architectural organization:**
- `src/`
- `services/`
- `frontend/`
- `tests/`
- `docs/`
- `logs/`
- `reference/`

**Ownership mechanism:**
`CONTRIBUTION_GUIDE.md`

**Reason:**
Separate software architecture from team ownership and make the repository suitable for collaborative Git-based development.

**Impact:**
The repository now looks like a coherent solo-developed software project while maintaining explicit team ownership documentation.\n


### Date: 2026-08-16
**Experiment / Decision:**
API Service — REST/WebSocket Skeleton

**Context:**
`services/api` is the primary REST and WebSocket interface between the client/dashboard and the Gateway. Before today it contained only a README.

**Problem:**
The team needed a minimal, running foundation for the API layer — validated against the Gateway's expected request shape and the planned WebSocket event flow — without finalizing schemas or building real Gateway integration yet.

**Initial approach:**
Reviewed the API and Gateway READMEs to map the request flow (Client/Dashboard → API → Gateway → Orchestration)

**Decision:**
Initialized `services/api` as a Node.js + TypeScript project (Express + `ws`). Built a minimal skeleton:
- `GET /health` — working
- `POST /execute` — stubbed (TODO: validation, Gateway forwarding)
- `GET /status/:execution_id` — stubbed (TODO: status lookup)
- WebSocket upgrade handling on `/stream/:execution_id` — connects and logs, no event emission yet

No Gateway integration or schema finalization done yet, per agreement — foundation only.

**Impact:**
`services/api` now boots and exposes the interface shape the rest of the team can build against.