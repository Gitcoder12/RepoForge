# RepoForge — Whole-Project Progress

**Snapshot:** 2026-11-20  
**Default branch:** `main`  
**Active work branch:** `feat/repobox-isolated-workspaces`  
**Tracking PR:** [#20 — RepoBox](https://github.com/Gitcoder12/RepoForge/pull/20)  
**Scope:** Whole RepoForge project, not just RepoBox.  
**Estimate:** **40%** — engineering maturity estimate, not test coverage or a claim of production readiness.

## Progress meter

```text
RepoForge  [████████░░░░░░░░░░░░] 40%
```

## Official product roadmap

| Version | Focus | Evidence required to call it complete |
|---|---|---|
| V1 | Basic AI repository automation | A documented, installable workflow that performs a bounded repository task through an explicitly selected model provider and reports its result |
| V2 | Repository intelligence and analysis | Reproducible scans and useful, evidence-backed repository findings with clear limitations |
| V3 | Autonomous AI repository engineering workflow | Model-assisted planning, isolated candidate edits, validation, reviewable diffs and recoverable execution in one tested workflow |
| V4 | Advanced improvement selection and intelligence | Evidence-ranked improvement candidates, confidence and risk estimates, and measurable prioritisation quality |
| V5 | Multi-agent engineering workflows | Integrated role-based agents with bounded handoffs, independent review, traceable artifacts and human approval |
| V6 | Autonomous software engineering platform | End-to-end orchestration with hardened isolation, policy enforcement, transactional recovery, observability and repeatable evaluations |

The version ladder is the product direction, not a statement that any version is already released. A capability only counts when it is integrated and verified on the default branch.

## Capability ledger

| Capability | Estimate | Current evidence / remaining work |
|---|---:|---|
| Canonical package and CLI | 100% | Canonical `src/repoforge` package and CLI are on main via merged PR #3; continue compatibility and packaging checks |
| Repository scanning and analysis | 60% | Scanner and analysis components exist; strengthen large-repository handling, accuracy and reproducible scoring |
| Real model-provider runtime | 55% | Explicit provider adapters and routing exist; broaden integration testing and provider error/retry behavior |
| TestForge and validation | 55% | Multi-language test discovery and bounded opt-in execution exist; no OS-level sandbox yet |
| Blacksmith repair engine | 25% | Auditing and narrow create-only hygiene repairs exist; general semantic code repair is not implemented |
| Coding / multi-agent workflows | 35% | Agent and staged-approval work is proposed in PR #5; it is not part of the verified mainline end-to-end workflow |
| RepoBox | 30% | Local clone import, manifest inventory and detached task worktrees exist in PR #20; hardening changes are now proposed, but exact-head CI and review remain |
| Execution safety, checkpoints and rollback | 25% | Path checks and validation components exist; legacy pipeline checkpoint failure handling and rollback guarantees need repair and regression tests |
| End-to-end reliability | 20% | More real repository workflows, failure injection, provider integration and independent review required |
| Release readiness | 10% | Packaging, security, UX, docs and supported-platform verification remain |

**Whole-project estimate: 40%.** The ledger is a reasoned engineering estimate. It is not the arithmetic average of line counts, PRs or test counts. Percentages will not increase just because code or tests were added; exact-head CI, review and integration evidence are required.

## Current implementation record

### RepoBox v0.1 foundation

- Local Git checkout import into a managed clone store.
- Manifest-backed repository inventory.
- Detached task worktrees so candidate edits are separated from both the original checkout and managed base clone.
- CLI entry point: `repobox`.
- Regression tests cover source isolation, workspace creation, traversal rejection, unknown repositories and duplicate workspaces.
- Current PR hardening adds clean-source checks, before/after HEAD consistency checks, partial-clone cleanup, unique temporary manifest files, atomic replacement, cross-process manifest locking, schema/path validation and concurrency/failure tests.
- Documentation: [docs/REPOBOX.md](docs/REPOBOX.md).

**Limitations:** RepoBox is not an OS/container sandbox. It does not run repository code, approve patches, or promote changes into source repositories. A stale manifest lock after a crashed process requires operator review and manual cleanup. The current PR is a draft and must be reviewed before merge.

## Release gates still required

1. Finish RepoBox lifecycle safety: workspace cleanup, quotas, integrity checks and crash recovery.
2. Add isolated execution for untrusted repository code; default deny network and secrets; enforce resource limits and process cleanup.
3. Add reviewable patch objects with explicit permissions and human approval.
4. Implement transactional apply / rollback with byte-for-byte restoration tests and recovery after interrupted operations.
5. Wire real model-assisted plans into the safe candidate workflow; no mock success or silent paid fallback.
6. Add end-to-end tests against disposable repositories across supported Python versions and provider configurations.
7. Complete security review, documentation audit and release packaging.

## Update protocol

- Update this file in the same work branch/session whenever project code is changed.
- Change a capability percentage only when implementation evidence supports it; record the code commit and exact CI run.
- A green CI result applies only to the exact tested commit. Later commits remain unverified until rechecked.
- Never count a draft PR or generated code as shipped.
- Do not modify forked repositories or repositories outside RepoForge and ARK.
- Do not merge to `main` without review and verified checks.

## Latest verified baseline

- Main at snapshot: `82148f6b8ca284d9865988d5c021c5fd450e1e56`.
- Earlier RepoBox CI run [44600451416](https://github.com/Gitcoder12/RepoForge/actions/runs/44600451416) passed four Python matrix jobs on commit `96cafb64f8deeb105982ee92c790925382567da7`.
- The new RepoBox hardening commits are: code `b73d4d4a667fe4e82c4642f33c95e808473ae52e`, tests `1b8a02e90e25c78d8cbe6cba41e0198ff941e0ae`, documentation `c6ae6e7b7a657cc7c2beafdef084b3b904e39078`.
- These commits have not yet been validated by a CI run on the resulting PR head. Do not treat the newly added tests as passing until that exact-head run is green.
- PR #20 remains open and draft. No merge to `main` has been made by this work.
