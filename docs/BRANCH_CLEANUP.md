# RepoForge — Branch Cleanup Inventory

**Audit date:** 2026-11-27  
**Default branch:** `main`  
**Release branch:** `release/omega-1.0`

## Inventory

- Total branches including `main`: 52
- Branches other than `main`: 51
- Branches with an open pull request: 9
- Branches whose associated pull request was merged: 34
- Branches associated with a closed, unmerged pull request: 4
- Branches with no matching pull request in the first 100 all-state PR results: 4

## Open pull-request branches — preserve

- `ai-upgrade-2026-11-13 (PR #5)`
- `chore/remove-emoji-glyphs-2026-11-13 (PR #6)`
- `docs/branch-activity-2026-11-18 (PR #18)`
- `docs/portfolio-operating-kit-2026-11-13 (PR #8)`
- `feat/execution-profiles-stop-points (PR #37)`
- `feat/global-repository-intelligence (PR #31)`
- `feat/repobox-isolated-workspaces (PR #20)`
- `feat/repoforge-sentinel-mvp (PR #22)`
- `release/omega-1.0 (PR #50)`

These branches are active review work. Do not delete or rewrite them as part of release cleanup.

## Merged pull-request branches — prune candidates

- `chore/repository-organization (PR #29)`
- `docs/consolidate-command-guide (PR #42)`
- `docs/current-status-2026-11-20 (PR #25)`
- `docs/current-status-2026-11-22 (PR #35)`
- `docs/interview-demo (PR #49)`
- `docs/local-launch-instructions (PR #27)`
- `docs/project-status-2026-11-16-repoforge (PR #10)`
- `docs/quick-command-guide (PR #41)`
- `docs/repository-comparison-2026-11-19 (PR #19)`
- `feat/blacksmith-megazord-engine (PR #14)`
- `feat/ecosystem-capability-adapters (PR #32)`
- `feat/forge-command-mainline-v2 (PR #40)`
- `feat/instant-test-engine (PR #15)`
- `feat/model-lab-2026-11-22 (PR #36)`
- `feat/orchestrator-real-provider-integration (PR #13)`
- `feat/provider-standby-routing (PR #17)`
- `feat/rag-fastmcp-knowledge-engine (PR #28)`
- `feat/random-repo-audit-memory-contexts (PR #47)`
- `feat/real-provider-runtime (PR #12)`
- `feat/repo-dictionary-codebase-indexer (PR #45)`
- `feat/repoforge-discipline-enforcement (PR #23)`
- `feat/repoforge-mastery-foundation (PR #9)`
- `feat/repoforge-truthstream-evidence-bridge (PR #24)`
- `feat/resources-intelligence-hub (PR #34)`
- `feat/runtime-resource-governor (PR #33)`
- `feat/system-health-preflight (PR #30)`
- `feat/universal-language-adapters (PR #46)`
- `feat/upgradeforge-ranked-improvements (PR #26)`
- `fix/canonical-package-layout (PR #3)`
- `fix/explicit-target-test-execution (PR #11)`
- `fix/windows-case-collision-python-version (PR #43)`
- `fix/windows-pytest-and-validator-diagnostics (PR #44)`
- `phase1/safe-rsi-step (PR #48)`
- `rulebook/engineering-constitution (PR #21)`

A merged PR does not by itself prove that its head branch is disposable. Before pruning, verify that the branch has no unique commits or unmerged follow-up work and that it is not used as a base by another open PR.

## Closed, unmerged pull-request branches — inspect individually

- `feat/forge-command-mainline (PR #39)`
- `feat/forge-end-to-end-pipeline (PR #38)`
- `feat/resilience-robotics-blueprint (PR #16)`
- `security/action-runner-path-guard (PR #1)`

Do not delete automatically. A closed, unmerged PR may contain work that was intentionally retained, superseded, or abandoned.

## Unlinked branches — inspect individually

- `docs/upgrade-plan`
- `feat/extreme-testing-lab`
- `feat/fortress-workspaces-learning`
- `feat/interaction-control-boundaries`

These branches were not associated with a pull request in the first 100 all-state PR results. This is not proof that they are stale. Compare each against `main` and check for unique commits before any pruning.

## Cleanup rules

1. Keep `main` and the dedicated release branch.
2. Preserve every branch associated with an open PR.
3. Never delete a branch that is the base of another open PR.
4. Prune only branches proven merged or fully superseded, after checking unique commits and references.
5. Preserve unique work in Git history before removing a branch reference.
6. Do not use force-push to rewrite shared history.
7. Record every pruned branch, source SHA, associated PR, and reason in this file.

## Tooling limitation

The connected GitHub actions currently available in this session support branch creation and repository reads, but do not expose a branch-delete operation. This inventory therefore makes no destructive branch changes. Use GitHub's branch settings/UI to prune only the individually verified candidates.
