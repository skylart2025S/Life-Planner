# GitHub delivery setup

Target repository: https://github.com/skylart2025S/Life-Planner

The repository was accessible through Git and empty when cloned on 2026-11-19. No existing code, specs, commits, or branches were available to review.

## Bootstrap and normal delivery

1. Review and test this foundation locally. Create the initial reviewed commits on `main`, then push to bootstrap the empty repository.
2. For subsequent tasks, create `agent/LP-<id>-<short-description>` branches from current `main`.
3. Commit coherent completed units with tests and relevant documentation. Push the task branch; open a pull request with its review report.
4. Observe GitHub checks, resolve review findings, and merge only under the agreed merge policy. Current default: user authorizes merges; agents may prepare commits, branches, and PRs.

The GitHub connector is not connected in this session. Git access can clone/push the repository, but does not expose PRs, issue discussions, or check results. Connect the GitHub plugin or authenticated GitHub CLI to enable those parts of the team workflow. Do not claim a PR or CI result based only on a successful push.

## Repository settings still needed

Require the foundation test job and review before merges to main. Disable force pushes to the protected branch. Assign actual trusted GitHub identities before adding CODEOWNERS; no account names are fabricated here. These settings have not been applied.

CI uses Python 3.12 and standard-library tests. Workflow structure follows [GitHub's Python workflow documentation](https://docs.github.com/en/actions/tutorials/build-and-test-code/python). No AI API keys or external provider credentials are required for the foundation checks.
