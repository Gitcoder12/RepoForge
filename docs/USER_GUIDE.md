# RepoForge User Guide

The root README is intentionally short. This file is the operational manual.

## 1. Install

Python 3.10 or newer is supported.

### Windows PowerShell

```powershell
git clone https://github.com/Gitcoder12/RepoForge.git
cd RepoForge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### macOS / Linux

```bash
git clone https://github.com/Gitcoder12/RepoForge.git
cd RepoForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 2. Inspect with Blacksmith

```bash
repoforge blacksmith /path/to/repository
```

This is a read-only dry run. It scans bounded repository metadata, derives language and capability hints, calculates a deterministic RepoRank from engineering-hygiene signals, and shows a repair plan.

The only automatic repair currently supported is creating a generic `.gitignore` when one is missing:

```bash
repoforge blacksmith /path/to/repository --apply
```

It does not overwrite existing files, delete files, install dependencies, run target tests, or ask a model to perform general code repair. Missing tests and CI are review-required recommendations, not generated placeholder files.

## 3. Compare repositories with Megazords

```bash
repoforge megazords /path/to/ARK /path/to/RepoForge
```

Supply 2–30 local repository directories. Megazords uses repository names, README text, manifests, languages, and file structure to estimate capability complementarity. It reports candidate patterns and integration risks. It does not clone, copy, merge, install, or run either repository.

## 4. Inspect providers and run model workflows

```bash
repoforge providers
repoforge generate --help
repoforge model-lab --catalog
```

Select providers explicitly; model requests can incur charges. Configure credentials in environment variables or a local ignored `.env` file. Never paste API keys into source code or commit them.

A model-target comparison uses explicit provider/model names:

```bash
repoforge model-lab --target provider:model --output model-lab.json
```

The Model Lab is a controlled smoke suite, not a general model leaderboard or safety certification.

## 5. Run the integrated Forge workflow

Default preview (no provider and no target writes):

```bash
repoforge forge /path/to/repository "Review the repository structure and propose prioritized improvements"
```

For a model-generated proposal, select a provider explicitly. Apply only after reviewing the proposal and authorizing exact paths:

```bash
repoforge forge /path/to/disposable-repository "Improve the README" --provider deepseek --apply --approve README.md
```

Use a disposable repository or clean feature branch for write tests. Inspect `git diff` immediately after application.

## 6. Test discovery and validation

```bash
repoforge test /path/to/trusted-repository
repoforge validate /path/to/trusted-repository
```

Test discovery is metadata-only. Validation is static by default. Do not add `--run-tests` or `--execute` unless you own and trust the target repository.

## 7. Test RepoForge itself

```bash
ruff check src/repoforge tests
ruff format --check src/repoforge tests
pytest -q
repoforge --help
repoforge version
repoforge providers
```

The release workflow also scans the actual ARK and RepoForge checkouts, runs Blacksmith's create-only repair against a disposable fixture, and asks Megazords to compare the two repositories. The resulting JSON is retained as a workflow artifact.

## 8. Critical execution boundary

TestForge and Forge can execute target-repository test code only when explicitly requested. That execution is **not OS-sandboxed**. Do not run tests or arbitrary build commands from untrusted repositories. Blacksmith and Megazords are metadata-analysis workflows; they are not substitutes for security review or integration testing.
