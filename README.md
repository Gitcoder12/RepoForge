# RepoForge

**Local-first repository engineering toolkit** for inspecting repository structure, measuring engineering-hygiene signals, proposing bounded repairs, and comparing possible repository combinations.

## Quick start

```bash
python -m pip install -e ".[dev]"
repoforge --help
repoforge blacksmith /path/to/repository
repoforge megazords /path/to/repository-a /path/to/repository-b
```

## Documentation

- [User guide](docs/USER_GUIDE.md) — install, CLI, providers, workflows, and safe usage
- [Omega 1.0 scope and stop line](docs/OMEGA_SCOPE.md) — exactly what works and what does not
- [Blacksmith & Megazords reference](docs/BLACKSMITH_MEGazords.md) — scoring, repair and comparison behavior
- [Release readiness](docs/RELEASE_READINESS.md) — acceptance gates
- [Model Lab](docs/MODEL_LAB.md) — explicit model endpoint evaluation
- [Contributor guide](START_HERE.md) — source map and contribution workflow
- [File index](FILE_INDEX.md) — alphabetical repository inventory

## Current status

Package metadata remains **0.6.0**. Omega 1.0 is a stabilization target, not a published or verified release. Blacksmith's automatic write is limited to creating a missing generic `.gitignore`; Megazords produces heuristic recommendations and does not combine or modify repositories. Test execution against target repositories is not OS-sandboxed.
