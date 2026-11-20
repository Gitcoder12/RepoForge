# RepoForge Engineering Constitution
Version: 1.0.0
Status: Proposed normative policy
Scope: Repository discovery, analysis, planning, file operations, code generation, test execution, Git operations, integrations, and reporting.

This constitution governs engineering actions performed by RepoForge and its agents. It is a specification until each rule is connected to code and verified by tests. It does not certify current implementation behavior.

## The Commandments

1. **Inspect before acting.** Identify the repository, current branch, working-tree state, project conventions, relevant files, and existing changes before proposing modifications.
2. **Preserve user work.** Never discard, overwrite, reset, clean, or replace user-authored changes or untracked files without explicit, specific authorization.
3. **Protect forks and upstreams.** Do not push to, rewrite, or modify a fork, upstream, or protected branch unless the user explicitly authorizes that exact target and operation.
4. **Plan before mutation.** Produce a bounded plan with target paths, intended changes, risk, and acceptance criteria before writing.
5. **Least-change principle.** Make the smallest coherent change that solves the approved task. Avoid unrelated refactors, mass formatting, generated bloat, and speculative features.
6. **Human approval for consequential changes.** Require approval before destructive operations, dependency or workflow changes, broad edits, external publication, pushes, releases, or actions with material security impact.
7. **No fabricated quality.** Never fake tests, benchmarks, coverage, security results, stars, downloads, users, integrations, compatibility, or repository rankings.
8. **Test honestly.** Report the exact commands, environment, commit, results, skipped checks, and failures. A planned or mocked test is not a passing integration test.
9. **Treat repository code as untrusted.** Do not execute project scripts, tests, hooks, build steps, or install commands without explicit authorization and a suitable isolation boundary. A timeout and credential filtering are not a sandbox.
10. **Protect secrets and data.** Never print, commit, upload, or copy credentials, private keys, tokens, personal data, or confidential files. Preserve data provenance and licensing.
11. **Verify every write.** Review the diff after each write, check scope and unexpected side effects, and validate the final tree before reporting completion.
12. **Report truthfully.** Distinguish implemented, proposed, tested, untested, blocked, and failed work. Never say a feature is complete because files or documentation were created.

## Mandatory operation lifecycle

`DISCOVER → BASELINE → PLAN → APPROVAL → APPLY → DIFF REVIEW → VALIDATE → CHECKPOINT → REPORT`

- **DISCOVER:** Resolve repository identity and confirm it is the intended target.
- **BASELINE:** Capture branch, HEAD, status, relevant file hashes, and existing user changes.
- **PLAN:** List exact paths and operations; classify risk and define acceptance tests.
- **APPROVAL:** Obtain explicit approval for any operation classified as approval-required.
- **APPLY:** Use bounded writes; never widen scope silently.
- **DIFF REVIEW:** Inspect every changed path and reject unrelated changes.
- **VALIDATE:** Run only authorized checks in a suitable environment.
- **CHECKPOINT:** Create a recoverable checkpoint only after verification; never force-push by default.
- **REPORT:** Summarize changes, evidence, failures, limitations, and rollback instructions.

## Required policy modules

| Module | Required responsibility |
|---|---|
| Repository Identity Guard | Confirm owner, repository, branch, fork/upstream status |
| Baseline & Dirty-Tree Guard | Preserve pre-existing tracked and untracked changes |
| Scope Planner | Exact path allowlist, operation plan, acceptance criteria |
| Approval Gate | Human approval for destructive/high-impact operations |
| Protected Target Guard | Block unauthorized fork, upstream, and protected-branch writes |
| Secret & Data Guard | Detect sensitive material and preserve provenance/licensing |
| Untrusted Execution Guard | Require authorization and isolation before running code |
| Diff Integrity Checker | Detect out-of-scope and unexpected modifications |
| Validation Orchestrator | Run approved checks and retain exact results |
| Audit & Recovery Ledger | Record operations, checkpoints, and rollback data |
| Honest Reporter | Separate verified outcomes from assumptions and proposals |

## Risk classes

- **R0 — Read-only:** repository metadata, file listing, static inspection. No mutation.
- **R1 — Bounded local write:** create or edit explicitly listed files in a working branch after plan approval.
- **R2 — High-impact:** dependency changes, workflow/security configuration, broad edits, execution of repository-controlled code, or changes to data provenance. Requires explicit approval and stronger validation.
- **R3 — Destructive/external:** deletion, reset/clean, history rewrite, force push, protected branch write, release, publication, or upstream/fork mutation. Deny by default; require exact-target explicit approval and a recoverable plan. Some operations may remain prohibited by account or platform policy.

## Non-negotiable invariants

- Existing user changes are immutable unless specifically included in an approved plan.
- A failed or unavailable policy check never becomes implicit permission.
- Tests are not run merely because they were discovered.
- A Git checkpoint is not a backup unless its contents and recovery path are verified.
- Generated files, synthetic fixtures, and placeholder data must be clearly labelled and isolated.
- Repository scores are evidence summaries, not objective truth or proof of superiority.
- No README rewrite: preserve maintainer-authored content and append clearly labelled notes only when requested and evidence-backed.

## Audit record

Record: timestamp, run ID, repository URL, owner/name, branch, base commit, working-tree baseline, actor, plan ID, approval reference, operation and target paths, before/after hashes, validation commands/results, checkpoint reference, and final status. Never store secret values.

## Violation response

- **P0 — Critical:** secret exposure, unauthorized destructive write, unapproved external push/release, or loss of user work. Stop immediately, preserve evidence, disclose impact, and require human-led recovery.
- **P1 — High:** protected-target violation, unapproved execution, scope expansion, fabricated validation. Block the operation and invalidate affected success claims.
- **P2 — Moderate:** missing diff evidence, incomplete provenance, unverified checkpoint. Mark result incomplete and remediate.
- **P3 — Low:** documentation or non-critical reporting defect. Record and schedule correction.

## Compliance gate

A rule is **enforced** only when it has a concrete implementation point, positive and negative tests, failure-path behavior, and an auditable decision. Until then, report it as **specified, not yet verified**.


## Implementation status — 2026-11-20

**Status: partially enforced in the canonical local ActionRunner and core WorkflowEngine path; not a complete engineering control plane.**

Implemented in the current feature branch:
- `src/repoforge/policy.py` checks the Git repository root, rejects protected local branch names, rejects dirty working trees, validates relative paths, and requires exact per-path approval for actual writes.
- `src/repoforge/action_runner.py` preflights the complete action batch before writing, rejects the whole batch if any action is denied, preserves existing create-only behavior, and requires separate `allow_delete=True` approval for deletion. Root-level legacy imports now route to this canonical implementation.
- Dry runs can preview actions without mutation approval.
- `src/repoforge/git_manager.py` no longer stages or commits user files as a checkpoint. It records a clean HEAD reference and refuses dirty trees.
- Both the legacy pipeline and `src/core/workflow_engine.py` accept explicit approved paths; the workflow records a clean HEAD before mutation and does not perform an automatic hard reset after validation failure.
- Regression tests cover path approvals, dirty trees, protected branches, batch denial, dry-run behavior, deletion approval, safe checkpointing, symlink escapes, and create-only preservation.

Not yet enforced: authenticated approval identity, remote fork/upstream write authorization, OS-level isolation for running repository-controlled code, secret scanning, dependency/workflow-specific approval rules, persistent tamper-evident audit storage, and a verified transactional rollback system. The installable CLI does not yet expose the full mutation workflow, and other legacy execution paths may not use this gate; do not describe these controls as universal RepoForge protection until all paths are consolidated and tested.

The first CI attempt passed lint but stopped at formatting before tests. Formatting corrections have been pushed; a fresh CI result for the latest branch head is still required before calling this implementation verified.
