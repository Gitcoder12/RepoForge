# RepoForge Omega 1.0 — Release Readiness

**Working branch:** `release/omega-1.0`  
**Baseline:** `main` at the time this branch was created  
**Status:** Release preparation; not yet a release candidate

## Release policy

This branch is limited to stabilization, correctness fixes, regression tests, documentation, repository organization, and release evidence. Do not add new product features during this release cycle.

RepoForge must be described accurately: repository inspection and selected bounded workflows are implemented, but heuristic scores are not proof of software quality, and test execution against a target repository is not OS-sandboxed.

## Initial findings

| Area | Observed state | Release implication |
|---|---|---|
| Package metadata | `pyproject.toml` reports version `0.6.0` | Do not publish 1.0 until acceptance gates pass |
| Release metadata | No verified release tag was recorded in the initial audit | Create a release tag only after the final gates pass |
| CI | Mainline quality workflow was green across Python 3.10–3.13 in the latest audit | Re-run on this branch and retain exact run evidence |
| TestForge | Test discovery is read-only by default; explicit execution runs repository-controlled code | Keep the warning prominent; do not imply sandboxing |
| ActionRunner | Current implementation preflights the batch, then applies actions sequentially; later write failures can leave earlier actions applied | Add regression coverage and define the partial-application contract; do not claim transactionality |
| Path handling | Resolved paths are checked against the repository root | Retain traversal and symlink-escape tests; review filesystem race boundaries |
| Blacksmith | Current documented repair scope is narrow; arbitrary semantic code repair is not implemented | Do not market it as a general autonomous repair engine |
| README | Contains historical status snapshots, roadmap claims, and examples that may not reflect current mainline behavior | Consolidate current capability statements and clearly label historical/proposed work |

## Required acceptance gates

- [ ] Clean clone and documented installation succeed on Python 3.10–3.13.
- [ ] Ruff lint and formatting checks pass.
- [ ] Full pytest suite passes on the supported Python matrix.
- [ ] Installed CLI commands work: `--help`, `version`, `providers`, and documented command help.
- [ ] Read-only repository inspection and test discovery work on a disposable sample repository.
- [ ] Approved write workflow is tested on a disposable repository with exact before/after diffs.
- [ ] Path traversal, absolute paths, symlink escapes, existing-file create, missing-file modify, and deletion policy have regression tests.
- [ ] Partial batch failure and rollback behavior are explicitly tested and accurately documented.
- [ ] Target-repository test execution warnings remain clear; no OS isolation is claimed.
- [ ] README, package metadata, changelog, and release notes agree on the release identity.
- [ ] Final release is tagged only after all gates are evidenced on the exact release commit.

## Scope boundaries

Allowed: bug fixes, regression tests, safe cleanup, documentation corrections, CI reliability, reproducibility, and release packaging.

Out of scope: new agents, new provider integrations, new autonomous capabilities, new dashboards, and roadmap expansion.

## Verification record

This file records the initial repository audit. It is not a test report. Fill in each gate with the exact commit, command, result, and CI run or reproducible evidence before calling Omega 1.0 ready.
