# AI Engineering Worklog

## Audit scope

Repository: RepoForge  
Base audited: `main`  
Working branch: `security/action-runner-path-guard`  
Date: 2026-11-13

The review covered repository structure, execution and validation paths, package metadata, tests, dependencies, and user-facing documentation.

## Confirmed fixes in this branch

- Confined ActionRunner file writes and deletes to the resolved repository root; absolute paths, traversal paths, and symlink escapes are rejected.
- Made `create` refuse to overwrite an existing file and made `modify` require an existing regular file.
- Changed the Python AST validator to handle nested attribute calls safely rather than raising while inspecting expressions such as `os.path.join`.
- Changed unexpected validation errors to fail closed instead of returning a successful validation result.
- Added focused regression tests for path traversal, symlink escape, create-overwrite protection, nested AST calls, and syntax-error handling.

## Audit findings requiring follow-up

### Architecture and packaging — high priority

- `pyproject.toml` declares the console script as `repoforge = "repoforge.cli:app"`, but the inspected source tree contains `src/cli/cli.py`, not `src/repoforge/cli.py`.
- The CLI module imports `..pipeline`, which needs a package layout that is not present in the inspected tree.
- README commands such as `python -m repoforge forge ...` do not match the declared CLI interface.
- Several modules and tests refer to `repoforge.*` while related files are stored under unrelated top-level source directories. This needs a deliberate package-layout migration, not a one-line entry-point substitution.

### Correctness and scoring — high priority

- The legacy `src/analysis/repository_health.py` expects metadata keys such as `readme`, `docs`, `tests`, `docker`, and `ci`, while the scanner emits `has_readme`, `has_docs_dir`, `has_tests_dir`, `has_dockerfile`, and `has_github_actions`.
- The same health engine reads `statistics.files` and `statistics.lines`, while the scanner emits `total_files` and `total_lines`. The result can therefore undercount repository size and mis-score health when this legacy path is used.

### Tests and CI — high priority

- No GitHub Actions workflow was present in the inspected RepoForge tree.
- The existing `tests/test.py` executes a patch operation at module import time and imports `repoforge.patch_engine`, while the inspected patch engine is under `src/fix/patch_engine.py`.
- A reproducible package install, import smoke test, and clean full-suite run are required before the project can claim CI-backed validation.

### Security and error handling

- The root-level ActionRunner previously accepted absolute/traversal paths and wrote directly to the resulting location; this is guarded in this branch.
- The validator previously treated unexpected validation exceptions as a passing result; this is guarded in this branch.
- The AST checks are heuristic review signals, not a complete sandbox or security boundary. RepoForge should not execute generated code solely because these checks pass.

### Dependencies, performance, and documentation

- The project has runtime dependencies but no declared development extra for test/lint tooling.
- Repository scanning reads many files repeatedly across separate passes; bounded traversal and explicit file-size limits should be unified.
- README usage and tested-repository claims need to be reconciled with the actual installable CLI and reproducible CI evidence.

## Validation status

- Regression tests have been added but have **not** been executed in a local checkout during this review.
- No passing CI result is claimed for this branch.
- The next required milestone is to establish one canonical import/package layout, add CI that installs the package and runs the complete suite, and then fix the resulting verified failures.

## Nine-gate summary

| Gate | Status | Finding |
|---|---|---|
| Architecture | Needs work | Package and CLI paths are inconsistent |
| Correctness | Needs work | Legacy health-score input keys mismatch scanner output |
| Tests | Needs work | Existing test entrypoint has import-time side effects and broken imports |
| Error handling | Improved | Validator now fails closed on unexpected errors |
| Security | Improved | ActionRunner path containment and overwrite protections added |
| Dependencies | Needs work | No development dependency group |
| Performance | Review needed | Multiple unbounded/repeated repository scans |
| Documentation | Needs work | README commands and claims need reproducible verification |
| CI/release | Blocked | No repository CI workflow found |

## Next actions

1. Decide and implement a single canonical Python package layout.
2. Add an install/import smoke test and a GitHub Actions matrix.
3. Repair the full test suite and verify the new security regression tests in CI.
4. Align health scoring with the scanner's actual schema.
5. Reconcile README installation and usage commands with the real CLI.
