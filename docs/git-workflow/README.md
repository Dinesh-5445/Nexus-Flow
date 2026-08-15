# Git Workflow

We use a branch-based workflow organized by architectural components, not by team members.

## Branch Naming
- `feature/gateway`
- `feature/pathway`
- `feature/provider-tools`
- `feature/watchdog`
- `feature/api`
- `feature/dashboard`
- `feature/telemetry`

## Workflow & Commits
- Branch isolation is strictly enforced.
- Merging via Pull Requests with required reviews on shared contracts (e.g., API schemas, event schemas).
- Commits must describe the actual change.
  - **Good:** `feat: add provider abstraction`, `feat: add event schema`
  - **Avoid:** `feat: dinesh work`, `feat: jyothi work`\n