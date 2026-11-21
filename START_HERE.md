# RepoForge — Start Here

RepoForge is a repository-analysis and engineering-assistance project. Start
with the installable package and the smallest supported workflow; do not infer
production readiness from roadmap text or example output.

## First five minutes

1. Read `README.md` for scope and limitations.
2. Install with `python -m pip install -e ".[dev]"`.
3. Run `repoforge --help` and `pytest -q`.
4. Read `docs/MAINTAINER_STATUS_2026-11-22.md` for the PR risk snapshot.
5. Read `docs/MODEL_LAB.md` before sending model API requests.

## Where code belongs

| Area | Purpose |
|---|---|
| `src/repoforge/` | Canonical installable product code |
| `src/repoforge/providers/` | Explicit model-provider adapters |
| `src/repoforge/security/` | Security controls and policy checks |
| `tests/` | Unit and integration tests; live API tests stay opt-in |
| `docs/` | Architecture, contributor guides, status and specifications |
| `scripts/integration/` | Explicit provider smoke tests and local demos |
| `configs/` | Non-secret example configuration |
| `playground/` | Disposable experiments only |
| `ideas/` | Unvalidated notes |

Older root-level Python modules and parallel `src/agents`, `src/core`,
`src/providers`, and `src/utils` trees remain in the repository. Treat
`src/repoforge/` as the canonical package for new development. Do not delete
or move older paths until imports, tests, scripts and external usage have been
audited.

## Safe development path

1. Make one focused change on one short-lived branch.
2. Add a regression test before implementation.
3. Run focused tests, then `ruff check src/repoforge tests`,
   `ruff format --check src/repoforge tests`, and `pytest -q`.
4. Keep repository-controlled test execution opt-in; TestForge is not an OS sandbox.
5. Open one reviewable PR. Do not stack unrelated features.

## Branch naming and cleanup

- `main` — stable integration baseline.
- `feat/<short-name>` — one feature per PR.
- `fix/<short-name>` — one bug fix per PR.
- `docs/<short-name>` — documentation-only work.
- Keep a branch while an open PR depends on it.
- After merge, verify the merge commit and main CI before deleting its source branch.
- Before deleting an orphan branch, compare it with `main` and preserve unique work.
- Avoid long-lived integration branches and branch-per-file changes.

## Current boundaries

Model Lab is a provider smoke-evaluation tool, not an autonomous-agent safety
benchmark. TestForge execution is not OS-sandboxed. Blacksmith repairs remain
bounded; no scan or score is a security certification.
