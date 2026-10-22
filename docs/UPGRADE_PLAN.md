# RepoForge upgrade plan
Audit date: 2026-10-22. Written on branch `docs/upgrade-plan`.

## Current state (measured)
- Version 0.6.0 in `pyproject.toml`. CLI entry point `repoforge = "repoforge.cli:app"`. About 13,400 lines of Python
- **The test suite cannot run.** Tests import `repoforge.*` (for example `repoforge.providers.mock`, `repoforge.stream`),
  but `src/` contains `agents/`, `providers/` and so on directly, with **no `repoforge/` package directory**.
  `pip install -e .` installs a package named `repoforge` with nothing importable: `ModuleNotFoundError: No module named 'repoforge'`
- **51 `.py` modules still sit at the repository root** (including `__init__ (1).py`), next to 51 in `src/`: an unfinished reorganisation
- `ruff check .`: 611 errors, 418 auto-fixable. Top rules: UP006 (198), UP035 (119), I001 (93), UP045 (49), F401 (41), BLE001 blind-except (34)
- 9 test files for about 13,400 lines. No CI

## Goals, in order
1. **Repair the package layout.** Create `src/repoforge/`, move the modules into it, diff every root-level module against its `src/` counterpart
   before deleting anything, and remove the root strays and `__init__ (1).py`.
   Done when `pip install -e . && pytest` passes locally.
2. **CI.** GitHub Actions (Python 3.11 and 3.12): install, ruff, pytest.
3. **Lint.** Run `ruff check --fix` for the safe fixes in one dedicated commit. Review all 34 `except Exception` sites by hand: handle or narrow them.
4. **Shrink the scope.** The project overlaps other orchestration tools and a crowded commercial field. Freeze new features. Keep the CLI plus
   the 2 or 3 agents that demonstrably work, and mark the rest experimental.
5. **Tests that matter.** Cover `scaffold()` with a temp-directory harness, the provider interface with the mock provider, and the CLI with typer's test runner.
6. **Evaluation.** One small, repeatable task that shows what RepoForge produces versus doing it by hand. Report real numbers only.

## Quality gate
`ruff check . && pytest`

## Rules for any contributor or AI model working from this plan
1. Work on a **new branch** (for example `feat/<topic>`). Never push to `main`. Open a pull request.
2. Run the quality gate before every push. Paste the real test output into the PR description.
3. Do not claim anything you did not measure. No invented benchmarks, no placeholder numbers.
4. Small, focused commits. Take git identity from `git log -1`; never invent an email address.
5. Never commit secrets, tokens, raw data or generated artifacts.
6. When a task is finished, tick its box here and note the date and PR number.

## Status
- [ ] Not started
