# RepoForge Omega 1.0 — Scope and Stop Line

**Branch:** `release/omega-1.0`  
**Package version:** `0.6.0`  
**Release state:** stabilization in progress; not a release candidate or published 1.0.0.

This is the capability contract for Omega. Implemented code, CI evidence, and operational limitations are deliberately distinguished.

## What works now

| Component | Verified implementation boundary | What it does not mean |
|---|---|---|
| Blacksmith scan | Bounded local file walk; ignores common generated directories and does not follow symlinks | Not a full static analyzer or security audit |
| RepoRank | Deterministic score from documentation, tests, CI, manifests, license, ignore rules, security process, and quality tooling | Not software quality, correctness, or security certification |
| Blacksmith dry run | Before/after structure and a repair plan | No target file is changed |
| Blacksmith apply | Creates a missing generic `.gitignore` with exclusive create semantics | No arbitrary code repair, overwrite, deletion, package install, or model call |
| Megazords | Compares 2–30 local repositories and ranks pairings using heuristic capabilities and shared languages | No code copying, cloning, merging, dependency resolution, or proof of compatibility |
| UpgradeForge | Produces a ranked recommendation catalogue with evidence and verification guidance | Does not implement recommended tests, CI, refactors, or security policies |
| Model Lab/providers | Explicit provider/model selection for configured model endpoints | Not an automatic model router or general-purpose model ranking |
| Forge workflow | Inspect → plan → propose → explicitly approve exact paths → validate/report | Target test execution is not OS-sandboxed; writes are not a universal transaction |

## Where Omega stops

Omega does not claim:
- General semantic repair across arbitrary repositories or languages.
- Autonomous multi-repository merging or integration.
- OS isolation for test/build commands from target repositories.
- Atomic all-or-nothing behavior across a multi-file action batch; later write failures may follow earlier applied actions.
- A security certification or a ranking that predicts delivery quality.
- That every UpgradeForge recommendation is implemented.
- That external model providers are configured or reachable merely because an adapter exists.

## Functional acceptance gates

1. Clean installation and supported Python matrix pass.
2. Ruff lint, formatting, and full pytest suite pass.
3. Installed CLI help, version, and provider status commands work.
4. Blacksmith scans the real ARK and RepoForge checkouts without modifying either.
5. Blacksmith applies its missing-`.gitignore` action only to a disposable fixture and reports the before/after rank delta.
6. Megazords compares the real ARK and RepoForge checkouts and emits one pairing report with capabilities, score, and integration risks.
7. Security/path tests and partial-failure behavior remain explicit; no untrusted repository tests are run.
8. Record exact commit and CI artifact before considering a release tag.

## Scoring interpretation

RepoRank is a fixed-weight presence score, not a measured quality outcome. Megazords fit scores are heuristic hypotheses based on text and structure. A high score only means more of the configured signals matched; it is not an instruction to merge repositories.
