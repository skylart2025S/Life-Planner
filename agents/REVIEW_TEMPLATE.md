# <task ID> — independent review

- Reviewer / session: <identity>
- Author: <different identity>
- Date (UTC): <timestamp>
- Scope and acceptance source: <task/spec references>
- Base / reviewed head: <exact commits; describe empty baseline if needed>
- Remote context: <PR/branch/checks observed and when; unavailable information>
- Verdict: <changes_requested|accepted|blocked; rationale>

## Acceptance coverage

| Criterion | Implementation evidence | Verification | Result |
| --- | --- | --- | --- |
| <requirement> | <file:line> | <check or observation> | <pass/fail/pending> |

## Findings

| ID | Severity / blocks acceptance? | Location | Trigger and impact | Evidence / required fix |
| --- | --- | --- | --- | --- |
| <R1> | <critical/high/medium/low; yes/no> | <file:line> | <specific scenario> | <reproduction and expected behavior> |

<If none, say no findings in reviewed scope; do not claim absence of all defects. Separate suggestions and unverified concerns.>

## Verification performed

- Local checks: <exact commands and observed results; identify author-only evidence>
- Remote checks: <observed run/status and revision; or unobserved>
- Not checked: <gaps and why>

## Fix verification and disposition

| Finding | Fix commit | Reviewer verification | Status |
| --- | --- | --- | --- |
| <R1> | <SHA> | <check/evidence> | <open/resolved> |

- Final reviewed head: <SHA>
- Remaining blockers: <findings, failed checks or missing evidence>
- Integration eligibility: <ready/pending plus authorization and required-check limits>
