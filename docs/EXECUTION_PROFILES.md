# RepoForge execution profiles

RepoForge separates three independent user controls:

- **Speed mode**: the time and iteration budget (Quick, Standard, Deep).
- **Evolution level**: requested scope (E0 Discover, E1 Stabilize, E2 Improve,
  E3 Optimize, E4 Evolve).
- **Stop point**: the last workflow stage RepoForge may reach.

## CLI

```bash
# Quick pass, stop after validation
repoforge profile --mode quick

# Thorough analysis, but stop before any patching
repoforge profile --mode deep --stop-after plan --evolution E3

# Standard profile with a smaller user budget
repoforge profile --mode standard --max-minutes 5 --max-iterations 0
```

The command prints a JSON execution contract. It does not run repository code,
apply patches or bypass the existing action-runner approval policy.

## Workflow stages

1. `inspect` — establish the repository baseline.
2. `plan` — produce a prioritized improvement plan.
3. `patch` — perform only changes authorized by the existing policy.
4. `validate` — run permitted validation.
5. `iterate` — begin another bounded improvement cycle.
6. `release_ready` — prepare a final report and handoff.

A stop point is inclusive: `--stop-after plan` includes inspection and planning,
then ends. Profiles expose only the stages they support. User-supplied budgets may
reduce, but never expand, the profile's hard limits.

Evolution depth does not force changes. E4 is a maximum requested scope, not a
goal; if the repository is already healthy, the correct outcome may be no change.

## Evolution levels

- **E0 Discover** — inventory and baseline; no changes.
- **E1 Stabilize** — bounded bug, test and reliability fixes.
- **E2 Improve** — targeted security, maintainability, documentation and test improvements.
- **E3 Optimize** — measured performance and architecture optimization.
- **E4 Evolve** — major architecture or capability proposals; proposal-first and human-approved.

Evolution level expresses the maximum requested scope. It does not require RepoForge to
make changes, and higher levels are not automatically better.
