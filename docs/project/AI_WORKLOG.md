# AI Engineering Worklog

## 2026-11-13 — Canonical package recovery

### Completed
- Added the installable `src/repoforge` package and declared `repoforge.cli:app` as the console entry point.
- Added `python -m repoforge`, `repoforge --help`, `repoforge version`, and `repoforge validate PATH`.
- Added deterministic offline provider/orchestrator primitives, structured logging, task stream management, typed models, validator, and packaged safety components.
- Made provider SDKs optional extras so core installation and CLI help do not require API credentials.
- Removed conflicting legacy `setup.py` metadata.
- Moved API/network/manual smoke scripts out of pytest collection into `scripts/integration/`.
- Replaced import-time logger/stream demos with deterministic unit tests.
- Removed the obsolete warning-only Flake8 workflow (which used `--exit-zero`) and added strict CI.
- Updated README commands to match the CLI that actually exists.

### Validation
- Exact validated code head: `68d4ed7e5ce4a2df4084a3817de6c20fd276d645`.
- GitHub Actions run: [43411116527](https://github.com/Gitcoder12/RepoForge/actions/runs/43411116527).
- Python 3.10, 3.11, 3.12, 3.13: editable package install passed.
- Ruff check and Ruff format check passed on all four versions.
- Pytest: 14 passed on each version.
- Installed CLI `repoforge --help` and `repoforge version` passed on all four versions.

### Explicit limitations / follow-up
- The legacy multi-agent `forge` workflow is not yet wired into the canonical CLI. The current stable CLI intentionally exposes only version and repository validation.
- OpenAI/Anthropic/Google provider adapters remain optional and need isolated integration tests with explicit credentials or local provider services.
- The package does not yet claim autonomous repository-editing capability from the new CLI.
- The separate security PR #1 remains independent and unmerged; this PR does not merge it.

## 2026-11-13 — Portfolio audit of current main and canonical-package PR

### Audit record
- Audited main HEAD: `51efe3251d695b696a16b42544ac6f55ae713f1c`.
- Recursive tree: 131 tracked files, a large legacy root-level module collection, a separate `src/` tree, tests, one enforcement workflow, and conflicting packaging/documentation entry points.
- Recommendation: IMPROVE / high-potential developer-tool flagship, but do not market autonomous repository editing as usable until the canonical package and safety gates are verified.

### Confirmed main-branch findings

#### P1 - Installed package and documented CLI mismatch
- Main `pyproject.toml` points to `repoforge.cli:app`, but the main source tree does not contain the corresponding `src/repoforge/cli.py` package.
- README documents `python -m repoforge --help`, but the canonical `repoforge/__main__.py` is absent on main.
- Legacy `setup.py` points to additional `repoforge.runner` and `repoforge.batch_runner` entry points not present in the canonical source package.
- Open issues #2 and #7 record the package-layout and test-collection failures.

#### P1 - Legacy ActionRunner lacks path confinement
- Main `action_runner.py` constructs paths with `self.repo_path / filepath` and writes or deletes them without resolving and checking that the target remains inside the selected repository root.
- Absolute paths or traversal components can escape the selected repository directory. This is a local file-integrity risk if untrusted or model-generated actions are executed.
- Do not run the legacy action runner against important directories until path confinement and explicit approval are enforced.

#### P2 - Repository hygiene and documentation drift
- `leaderboard.py` contains only whitespace.
- A second lowercase `readme.md` exists alongside `README.md` and contains only a very small stub.
- `features` and `usage` appear as root files rather than structured directories.
- README claims that several external repositories were tested and passed; this audit did not find supporting reproducible test artifacts for those claims.

### Existing repair work and CI evidence
- [PR #3](https://github.com/Gitcoder12/RepoForge/pull/3) adds a canonical `src/repoforge` package, stable limited CLI, offline provider primitives, validator, tests, and strict CI. It includes AI_WORKLOG.
- PR #3's latest inspected head is `6836ac3830476dd8555f764b0a9d44b4bcd75988`.
- GitHub Actions run [43458170296](https://github.com/Gitcoder12/RepoForge/actions/runs/43458170296) FAILED in all four Python jobs at `ruff format --check src/repoforge tests`.
- The log identifies two files requiring formatting: `tests/test_package.py` and `tests/test_stream.py`. Unit tests and CLI verification were skipped after the formatting failure. Lint passed; no test pass is claimed.
- PR #1 is a separate path-confinement/security change and must be reviewed independently; PR #3 does not implicitly merge it.

### Verification
- Inspected main README, pyproject, legacy ActionRunner, provider factory, recursive tree, open issues and PR metadata.
- No local tests were run in this audit.
- Independent final-head review: NOT COMPLETE.
- Main branch package install and CLI: NOT VERIFIED.
- PR #3 formatting check: FAILED; tests/CLI: SKIPPED.

### Next actions
1. Format the two failing test files on PR #3 and rerun the entire Python matrix.
2. Verify package install, `repoforge --help`, `python -m repoforge`, and `repoforge validate PATH` on the exact final head.
3. Independently review the path-confinement implementation in PR #1 and ensure the canonical package uses the same safe boundary.
4. Keep provider/network integrations out of unit-test collection and never require credentials for import or CLI help.
5. Clearly document that the current canonical CLI is limited; do not claim full autonomous forge workflow support until it exists and passes integration tests.
