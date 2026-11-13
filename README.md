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
