# RepoForge

**Early alpha · Python package recovery in progress**

RepoForge is an early-stage toolkit for repository validation and controlled AI-assisted engineering. The canonical package is being rebuilt before the legacy multi-agent workflow is reintroduced.

## What works today

- Installable `repoforge` Python package.
- `repoforge --help` and `repoforge version`.
- `repoforge validate PATH`: Python AST checks followed by the target repository's pytest suite.
- Offline `MockProvider` and explicit provider orchestration.
- Structured logging and task progress stream.
- Rule-based Warden and Crucible safety components.

## Not available yet

- The legacy autonomous `forge` workflow is not wired into the canonical CLI.
- OpenAI, Anthropic, Google and local-model adapters are not yet exposed through the canonical provider package.
- RepoForge does not automatically edit, commit, or merge repository changes.
- The static validator is heuristic and is not a complete security scanner or proof of code safety.

## Install

Python 3.10–3.13.

```bash
python -m pip install -e ".[dev]"
```

Optional provider SDKs:

```bash
python -m pip install -e ".[providers]"
```

## CLI

```bash
repoforge --help
repoforge version
repoforge validate /path/to/repository
```

Equivalent module invocation:

```bash
python -m repoforge --help
```

The validation command checks Python syntax and selected risky AST patterns, then invokes pytest in the target repository. It returns a failure if pytest is unavailable or tests fail.

## Five-stage project assembly

RepoForge can generate a provider-neutral prompt for each project stage and keep the five-stage workflow gated by explicit human approval.

```bash
repoforge pipeline init --project-name "Example Service" --description "A service that solves a defined problem" --target-environment "Docker on AWS" --stack "Python 3.12, FastAPI, PostgreSQL" --edge-cases "Concurrency, timeouts, malformed input"
repoforge pipeline prompt
repoforge pipeline submit --artifact-file blueprint.txt
repoforge pipeline approve --note "Architecture reviewed"
repoforge pipeline status
```

The stages are Blueprint, Foundation, Engine, Shield, and Deployment. Rejected artifacts can be revised with recorded feedback. The workflow stores artifacts locally and does not execute generated code or certify production readiness. See [ASSEMBLY_PIPELINE.md](docs/ASSEMBLY_PIPELINE.md) for the complete process.

## Package layout

```text
src/repoforge/
├── cli.py
├── base.py
├── models.py
├── orchestrator.py
├── logger.py
├── stream.py
├── validator.py
├── providers/
│   ├── base.py
│   └── mock.py
└── security/
    ├── warden.py
    └── crucible.py
```

## Development

```bash
python -m pip install -e ".[dev]"
ruff check src/repoforge tests
ruff format --check src/repoforge tests
pytest -q
```

CI validates package installation, lint, formatting, tests and installed CLI commands on Python 3.10, 3.11, 3.12 and 3.13.

## Safety notes

Warden and Crucible are rule-based guardrails. They can detect selected known patterns but cannot guarantee that prompts, model outputs, dependencies or repository changes are safe. Human review remains required for consequential changes.

## License

See [LICENSE](LICENSE).
