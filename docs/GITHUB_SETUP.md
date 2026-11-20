# GitHub delivery setup

Target repository: https://github.com/skylart2025S/Life-Planner

The repository was accessible through Git and empty when cloned on 2026-11-19. No existing code, specs, commits, or branches were available to review.

## Bootstrap and normal delivery

1. Review and test this foundation locally. Create the initial reviewed commits on `main`, then push to bootstrap the empty repository.
2. For subsequent tasks, create `agent/LP-<id>-<short-description>` branches from current `main`.
3. Commit coherent completed units with tests and relevant documentation. Push the task branch; open a pull request with its review report.
4. Observe GitHub checks, resolve review findings, and merge only under the agreed merge policy. Standing authorization from 2026-11-19: agents may merge independently reviewed PRs when all automated checks pass for the current head. Do not bypass branch protection or deploy.

GitHub CLI is installed and authenticated. Git push and authenticated GitHub API access were verified during bootstrap publication; the foundation workflow passed. Use the authenticated CLI for branches, pull requests, issues, and check results. Observe each PR/check result directly rather than inferring it from a successful push.

## Repository settings still needed

Require the foundation test job and review before merges to main. Disable force pushes to the protected branch. Assign actual trusted GitHub identities before adding CODEOWNERS; no account names are fabricated here. These settings have not been applied.

CI uses Python 3.12 and standard-library tests. Workflow structure follows [GitHub's Python workflow documentation](https://docs.github.com/en/actions/tutorials/build-and-test-code/python). No AI API keys or external provider credentials are required for the foundation checks.
