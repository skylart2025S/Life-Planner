# AI Life Planner delivery team

## Mandate

Build a chat-driven weekly planner in small, tested increments. Each change has one accountable owner, an independent reviewer, an explicit acceptance gate, and a written handoff. The user sets product direction; the coordinator translates it into bounded milestones. Development agents are contributors to this repository, distinct from the future product's AI intent and recommendation modules.

The standing roles below define responsibilities, not a claim that seven agents are continuously running. During an active session, the coordinator may invoke the roles needed for the selected milestone. Available concurrency limits determine how many run together; a role can be filled sequentially. Repository briefs alone do not create a scheduler, autonomous background workers, paid API calls, or GitHub access. The coordinator confirmed an ACTIVE hourly task heartbeat named `ai-life-planner-development-team` on 2026-11-19. It invokes bounded delivery cycles; it is not an always-running daemon, and configuration does not prove a particular run executed.

## Organization and ownership

| Role | Accountable for | Default boundary |
| --- | --- | --- |
| Coordinator | Task selection, assignments, progress, integration and milestone report | Task ledger, `docs/STATUS.md`, branch integration, shared delivery configuration |
| Product architect | Requirements, acceptance criteria, shared contracts and decisions | Product/architecture/API/backlog docs and `docs/decisions/` |
| Backend engineer | Planning correctness, persistence and authenticated service | `life_planner/`, `apps/api/`, related migrations and tests |
| Frontend engineer | Calendar, chat, preview and confirmation experience | `apps/web/` and related UI tests |
| Integration engineer | AI/provider adapters, import, outbox and synchronization | Assigned adapter files, `workers/` and related contract tests |
| Independent reviewer | Evidence-based correctness, privacy, regression and acceptance review | Read-only implementation review; own report file |
| Repository reviewer | Initial inventory and spec-to-code gap analysis | Read-only repository/GitHub discovery; own report file |

These are defaults, not permission to edit a whole directory. Every assignment names exact files or subdirectories. The coordinator reserves shared contracts, migrations, dependency manifests, CI, status, and integration files for one owner at a time. Engineers request changes to another owner's boundary. No contributor overwrites or reverts another's work.

## Decision and release authority

- The product architect proposes scope and documents assumptions; the coordinator selects work consistent with the user's request. Material product decisions unresolved by existing requirements return to the user with a concrete recommendation.
- Engineers may implement, test, commit and push assigned changes within the user's authorization. A commit or push is not review approval or release acceptance.
- Review must be performed by an agent other than the author for each implementation change. The coordinator cannot substitute author self-review for independent review.
- The coordinator integrates only reviewed work with passing required checks and existing merge authorization. On 2026-11-19 the user explicitly authorized merging independently reviewed PRs when all automated checks pass. Verify review coverage and checks for the current head; never bypass branch protection. Deployments remain unauthorized. The initial empty-repository bootstrap may be pushed to main after independent review. Repository permission changes, purchases and unrelated external messages are separate decisions.
- Any contributor may flag a blocking defect. Only new evidence, a verified fix or an explicit documented product decision resolves a finding; silence is not approval.

## What “a good product” means

Use the following gates instead of an unlimited instruction to keep coding. A milestone ends with a report and a selected next task; work continues within the active session and authorized scope. An unavailable service or decision is reported as blocked, never as completed.

| Milestone | Acceptance evidence |
| --- | --- |
| M0 — reviewed foundation (LP-100) | Repository/spec inventory; runnable demo; behavior tests; independent review with blocking findings resolved; actual commit/push status; remote checks observed or explicitly pending |
| M1 — durable private plans (LP-101/102) | Atomic durable apply/retry and restart/concurrency tests; owner derived from authentication; cross-user rejection tests; defined API contracts |
| M2 — usable planning journey (LP-103/104) | Week/calendar and chat; clarification; linked-change preview; explicit confirmation; loading/error states; keyboard-accessible journey; synthetic intent evaluations |
| M3 — connected routine planning (LP-105/106/108) | Account-scoped calendar import; recurrence/DST tests; confirmed idempotent sync with retries and visible failures; revoked-token/reconciliation tests |
| M4 — release candidate (LP-107/109/110) | Preference-grounded suggestions; validated undo/history; measured latency/load/cost budgets; backup restore and deletion checks; privacy/accessibility review; deployment runbook |

M0 is a development backbone, not the completed product. Numeric production budgets and provider/framework choices must be agreed and recorded before their release gates can pass. Split each milestone into backlog-sized tasks and do not begin dependent implementation until its contract is ready.

## Operating rhythm

Each hourly cycle reconciles the persistent reports and delivers at most one bounded work slice. Each completed work item produces a tested code-and-documentation commit on a task branch, an authorized push, an independent review, and a handoff. Each milestone produces a short executive report covering delivered behavior, verification, unresolved risks, and the next bounded objective. Update reports when results change; do not manufacture activity with empty commits or repeated unchanged status reports. See [the workflow](AGENT_WORKFLOW.md) for the exact lifecycle.
