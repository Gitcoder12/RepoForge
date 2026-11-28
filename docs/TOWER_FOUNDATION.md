# Tower Strategy: RepoForge Foundation

This document defines the order of work. Features are not considered complete because a module exists; each tower level must pass its acceptance gates before the next is built.

## Tower 0 — Safe foundation (current branch)

- Deterministic repository inspection and explicit mutation approval.
- Preflight every action before the first write.
- Snapshot mutation targets and roll back a failed batch.
- Keep dry-run behavior non-mutating.
- Run the existing Python 3.10–3.13 CI matrix and focused rollback/security regressions.

**Exit gate:** failed multi-file repairs restore original file bytes and permissions; create-only paths do not overwrite; traversal and protected-branch checks remain enforced; CI is green.

## Tower 1 — GitHub-native read-only engine

- Search/select installed repositories, branches, issues, and pull requests.
- Fetch PR diffs and changed-file metadata.
- Run Blacksmith, LangFix, TestForge discovery, static validation, and specialist reviews without executing target code.
- Publish evidence-backed check summaries as PR checks or comments.

**Exit gate:** read-only permissions, pagination, rate-limit handling, idempotent runs, and fixture-backed API tests.

## Tower 2 — Proposed repairs

- Generate patches against a disposable worktree.
- Show exact diff, affected paths, risk, tests, and model provenance.
- Require explicit approval of exact paths and patch digest.
- Never write to the default or protected branch.

**Exit gate:** approval binds to the reviewed patch; changed patch requires fresh approval.

## Tower 3 — Controlled execution

- Execute permitted tests in disposable, resource-limited containers.
- Enforce wall-clock, CPU, memory, disk, network, and output limits.
- Collect test logs and artifacts; destroy the environment after use.
- Apply accepted changes to a dedicated branch and open a pull request.

**Exit gate:** adversarial tests prove isolation boundaries and failed tasks leave the source repository unchanged.

## Tower 4 — Bounded autonomy

- Queue and orchestrate multi-step tasks with explicit budgets and retry limits.
- Use ARK policy decisions at every tool and mutation boundary.
- Stop on policy denial, uncertain state, quota exhaustion, or failed rollback.
- Produce a reproducible audit record for every run.

**Non-goal:** unrestricted self-modification, direct pushes to protected branches, or silent model/provider switching.

## Current scope

This branch strengthens the mutation foundation. It does not yet implement the GitHub API engine, container sandbox, or autonomous pull-request lifecycle. Those are separate towers with explicit acceptance gates.
