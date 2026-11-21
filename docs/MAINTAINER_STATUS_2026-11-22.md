# RepoForge — maintainer status and merge plan

**Snapshot date:** 2026-11-22  
**Default branch:** `main` at `ab3e7912055243d991b9eb91687e7bb171153ca6`  
**Open PRs at audit:** 13  
**Project classification:** active development prototype; no verified release tag recorded.

## What is in main

The current README describes repository inspection/health signals, TestForge command discovery, bounded Blacksmith hygiene repairs and Megazords comparison. Verify the exact command and behavior on the current default branch before presenting it as a supported workflow.

**Important safety boundary:** TestForge's explicit execution mode is not OS-sandboxed. It can run repository-controlled code. Do not execute tests from untrusted repositories. Blacksmith's repair scope is narrow; it is not arbitrary semantic code repair. A successful scan or score is not a security certification or proof of repository quality.

## Current CI failures confirmed from workflow logs

| PR | Feature | Latest observed CI | Finding | Action |
|---|---|---|---|---|
| [#34](https://github.com/Gitcoder12/RepoForge/pull/34) | Resources intelligence hub | Fail | Ruff F821: `timezone` referenced but not imported in `src/repoforge/resources.py` | Add correct import; rerun all Python versions |
| [#33](https://github.com/Gitcoder12/RepoForge/pull/33) | Runtime resource governor | Fail | Ruff formatting check reports `src/repoforge/resource_governor.py` would be reformatted | Run Ruff formatter; rerun matrix |
| [#31](https://github.com/Gitcoder12/RepoForge/pull/31) | Global repository intelligence | Fail | Ruff reports line-length and import-order issues in action runner and intelligence package | Fix lint; rerun matrix |

## Other open PRs

| PR | Feature | Audit disposition |
|---|---|---|
| [#32](https://github.com/Gitcoder12/RepoForge/pull/32) | Ecosystem analyzer adapters | Stacked on #31. Keep blocked until #31 is fixed/merged; update its base and rerun CI afterwards. |
| [#30](https://github.com/Gitcoder12/RepoForge/pull/30) | System Health | CI passed on inspected head; non-draft and mergeable in the prior live check. Recheck head/base and reviews before merge. |
| [#28](https://github.com/Gitcoder12/RepoForge/pull/28) | RAG + FastMCP | CI passed on inspected head; refresh against current main and rerun CI before merge. |
| [#26](https://github.com/Gitcoder12/RepoForge/pull/26) | UpgradeForge | CI passed on inspected head; refresh against current main and rerun CI before merge. |
| [#24](https://github.com/Gitcoder12/RepoForge/pull/24) | TruthStream Bridge | Draft; review evidence validation and safety boundaries before marking ready. |
| [#23](https://github.com/Gitcoder12/RepoForge/pull/23) | Discipline engine | Draft; run-scoped primitive, not production enforcement. |
| [#22](https://github.com/Gitcoder12/RepoForge/pull/22) | Sentinel scanner | Draft; verify scanner scope, false positives and test coverage. |
| [#20](https://github.com/Gitcoder12/RepoForge/pull/20) | RepoBox | Draft and reported non-mergeable/no CI in the inspected snapshot; validate locking, path confinement, crash recovery and workspace lifecycle. Not an OS sandbox. |
| [#18](https://github.com/Gitcoder12/RepoForge/pull/18) | Branch activity documentation | Stale documentation branch; consolidate or close after status docs are accepted. |
| [#10](https://github.com/Gitcoder12/RepoForge/pull/10) | Project status snapshot | Draft documentation branch; consolidate into this canonical status record or close as duplicate. |
| [#8](https://github.com/Gitcoder12/RepoForge/pull/8) | Project handbook | Legacy test collection fails because tests import removed package paths and initialize OpenAI without credentials. Fix tests/workflow; do not mask failures. |
| [#6](https://github.com/Gitcoder12/RepoForge/pull/6) | Emoji removal | Same legacy test collection failures as #8. Decide whether the formatting-only change is still useful; avoid merging unrelated legacy breakage. |
| [#5](https://github.com/Gitcoder12/RepoForge/pull/5) | Multi-agent foundation | **Hold.** Unresolved review findings include Terraform state secrets in model context, credential-bearing `.npmrc`/`.pypirc`/`.netrc`, inaccurate proposal-only README claims, missing provider-extra guidance, context-limit bypass for rejected artifacts, repository-cache collisions and unreported per-file truncation. Also targets a non-main base branch. |

## Merge and verification policy

1. Fix #34, #33 and #31 first; #32 depends on #31.
2. Revalidate #28 and #26 against the current main before merge. Do not rely on a green run from an older base SHA.
3. #30 is the cleanest immediate candidate from the inspected snapshot, but confirm its current head, CI and review state before merging.
4. Keep #5 blocked until every security/architecture finding is addressed and the PR is retargeted/rebased appropriately.
5. Do not mark all drafts ready. Review each feature's actual code, tests, threat model and operational limitations.
6. No PR feature is part of main until merged and re-tested on main.

## Branch hygiene recommendation

Keep `main` protected and use one short-lived branch per independently reviewable feature. Keep branches that back active PRs. After a PR is merged, verify the merged commit and CI, then delete its source branch. Close duplicate/stale documentation PRs after preserving useful content in one canonical document. Do not delete a branch merely because it is old: first check whether it contains unique unmerged work. Avoid creating a new branch for every small README/status correction; batch related documentation into one documentation PR.

## Audit limits

This snapshot records GitHub PR metadata, selected diffs/review threads and the workflow runs available at audit time. It is not a fresh local test run of every branch, and CI may change after this timestamp. Recheck the PR head SHA and workflow status immediately before merge.
