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
- Exact validated PR head: `5da92fadfcfa9cdedfcd91710613e2c5630ec5df`.
- GitHub Actions run: [43408948188](https://github.com/Gitcoder12/RepoForge/actions/runs/43408948188).
- Python 3.10, 3.11, 3.12, 3.13: editable package install passed.
- Ruff check and Ruff format check passed on all four versions.
- Pytest: 11 passed on each version.
- Installed CLI `repoforge --help` and `repoforge version` passed on all four versions.

### Explicit limitations / follow-up
- The legacy multi-agent `forge` workflow is not yet wired into the canonical CLI. The current stable CLI intentionally exposes only version and repository validation.
- OpenAI/Anthropic/Google provider adapters remain optional and need isolated integration tests with explicit credentials or local provider services.
- The package does not yet claim autonomous repository-editing capability from the new CLI.
- The separate security PR #1 remains independent and unmerged; this PR does not merge it.
