# Release-hardening findings

Audit scope: source inspection of `tower/phase-1-test-evidence` at `9a5afa8f33a960a50b85590bcde9c15ac82d854e`. This is a source-review record, not a claim that every finding has been reproduced dynamically.

## Release blockers

| ID | Severity | Finding | Evidence | Required closure proof |
|---|---|---|---|---|
| RF-RB-01 | Critical | Repository target tests are not sandboxed. | `src/repoforge/forge.py` documents that target tests are opt-in and not sandboxed; `src/repoforge/cli.py` restricts the option to trusted repositories. | Run untrusted tests only inside an OS/container/VM isolation boundary with no host secrets, restricted filesystem, network egress policy, CPU/memory/process/time limits and forced cleanup; adversarial escape tests. |
| RF-RB-02 | Critical | File mutation is protected by in-process path and approval checks, not an OS-level security boundary. | `src/repoforge/action_runner.py` resolves/checks paths and then writes/deletes them in the same process. | Use descriptor-relative/no-follow operations or a dedicated isolated worker; test symlink swaps and concurrent path replacement between preflight and write/delete. |
| RF-RB-03 | High | Approval is represented as caller-supplied path strings and a boolean delete flag, not an authenticated approval record. | `ActionRunner.run(... approved_paths, allow_delete)`; `PolicyEngine.evaluate_action(...)`. | Bind approval to authenticated principal, exact repo identity, commit/base SHA, action digest, path set, expiry and one-time nonce; reject replay and scope changes. |
| RF-RB-04 | High | Audit events are volatile and mutable in-memory lists. | `PolicyEngine.audit_events` is a bounded list; ActionRunner returns a copy of the current process history. | Durable append-only, tamper-evident audit with restart recovery and integrity tests. |
| RF-RB-05 | High | The broader legacy workflow surface requires an entry-point inventory before release. | The repository contains multiple execution surfaces (installable `ForgeWorkflow`, legacy root runners and `src/core/workflow_engine.py`). The older workflow imports modules not present in the installable `src/repoforge` package tree. | Decide which surfaces are supported; remove/retire or repair unsupported paths; test every advertised CLI/API entry point and prove all mutations pass through one policy gate. |

## Existing evidence

- The CI workflow reports 228 tests passing on each of Python 3.10, 3.11, 3.12 and 3.13 for the audited commit.
- Those are unit-test results for that commit and matrix. They do not close the blockers above or establish safe execution of untrusted repositories.
- The current CLI's explicit trusted-repository warning is appropriate, but it is not a sandbox.

## Next test campaign

1. Hostile test execution: filesystem escape, process spawning, environment/credential access, network access, resource exhaustion and cleanup after timeout.
2. TOCTOU tests: replace a checked directory/file with a symlink between preflight and mutation.
3. Approval replay/scope tests: wrong repo, wrong commit, changed content, expired approval, duplicate nonce, unauthorized delete.
4. Crash/restart tests for audit continuity and partially applied batches.
5. Entry-point coverage: every public CLI/API/legacy runner must route through the same policy boundary.

Do not mark a blocker closed until a regression test fails before the fix, passes after the fix, and the resulting CI artifact is retained with the exact commit SHA.
