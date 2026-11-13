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


## 2026-11-13 — Coding and research super-agent foundation

### Completed
- Added provider-agnostic Architect, Coder, and Reviewer workflow for coding tasks.
- Added evidence extraction, research synthesis, citation audit, and LaTeX formatting workflow.
- Added role-based provider routing so different models can handle architecture, implementation, review, extraction, synthesis, auditing, and formatting.
- Added bounded revision loops and fail-closed handling for malformed or contradictory reviewer output.
- Prevented LaTeX generation when the citation audit fails.
- Explicitly report that model review is not test execution and model-assisted citation review is not external bibliographic verification.
- Added offline unit tests for workflow ordering, revision handling, malformed output, audit gates, and provider routing.
- Removed emoji glyphs from the RepoForge agent protocol, skill definitions, and legacy action-runner source.

### Validation status
- Source files and tests were added to the isolated branch `ai-upgrade-2026-11-13`.
- Full Ruff and pytest execution remains pending because this environment cannot clone the GitHub repository.
- The new workflow does not modify repositories, execute generated code, commit changes, or merge pull requests automatically.
- The multi-agent upgrade is stacked on `fix/canonical-package-layout`; the canonical package recovery PR must land before this branch can be merged into `main`.
