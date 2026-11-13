# RepoForge

## Autonomous AI Repository Engineering Platform

RepoForge is an AI-powered repository engineering platform that analyzes software projects, understands repository structure, creates improvement strategies, executes engineering actions, validates changes, and generates detailed reports.

It combines repository analysis, AI workflows, safety validation, and Git checkpointing into a unified development tool.

---

# How It Works

```text
Repository
    |
    v
Repository Scanner
    |
    v
Intelligence Engine
    |
    v
Difficulty Analysis
    |
    v
AI Strategist
    |
    v
AI Orchestrator
    |
    v
Action Runner
    |
    v
Validator
    |
    v
Git Checkpoint
    |
    v
Report
```

---

# Features

| Component           | Purpose                                             |
| ------------------- | --------------------------------------------------- |
| Repository Scanner  | Detects files, languages, and repository statistics |
| Intelligence Engine | Evaluates repository quality and architecture       |
| Quality Scoring     | Generates repository health scores                  |
| Difficulty Engine   | Estimates repository complexity                     |
| AI Strategist       | Creates execution plans based on repository context |
| AI Orchestrator     | Coordinates AI operations                           |
| Action Runner       | Executes repository modifications                   |
| Validator           | Checks changes before completion                    |
| Git Manager         | Creates safe checkpoints                            |
| Reporter            | Generates execution reports                         |

---

# Intelligence System

RepoForge analyzes repositories using:

| Metric          | Description                    |
| --------------- | ------------------------------ |
| Repository Size | File count and code volume     |
| Languages       | Detects technology stack       |
| Documentation   | Checks project documentation   |
| Testing         | Evaluates testing signals      |
| Security        | Checks security-related issues |
| Maintainability | Estimates repository health    |

Example:

```text
Repository:

FastAPI-Test

Files:
3109

Lines:
654379

Languages:
Python
JavaScript
HTML
CSS


Quality Score:
87/100

Grade:
B
```

---

# Difficulty Levels

RepoForge automatically estimates repository complexity.

| Level   | Description              |
| ------- | ------------------------ |
| Normal  | Small repositories       |
| Hard    | Medium-sized projects    |
| Extreme | Large-scale repositories |

Example:

```text
Cal.com

Files:
7623

Lines:
4960332

Difficulty:
Extreme
```

---

# Installation

## Requirements

* Python 3.10+
* Git

Install:

```bash
pip install -e .
```

Verify:

```bash
python -m repoforge --help
```

---

# Usage

Run RepoForge:

```bash
python -m repoforge forge <repository> "<task>"
```

Example:

```bash
python -m repoforge forge ../FastAPI-Test "Analyze architecture and improve quality"
```

---

# Example Execution

```text
Repository Analysis

Files:
3109

Lines:
654379

Languages:
Python
JavaScript
HTML
CSS


Intelligence

Quality Score:
87/100

Grade:
B


Forge Actions:
Completed


Validation:
Passed


Git:
Checkpoint Created


Report:
Generated
```

---

# Change Tracking

RepoForge creates Git checkpoints after successful execution.

View changed files:

```bash
git show --name-only HEAD
```

View change summary:

```bash
git show --stat --oneline HEAD
```

View exact changes:

```bash
git show HEAD
```

Check uncommitted changes:

```bash
git status
```

```bash
git diff --stat
```

```bash
git diff --name-only
```

---

# Reports

RepoForge generates reports inside:

```text
.repoforge/

├── reports/
│   └── report_timestamp.json
│
└── backups/
```

Reports contain:

* Repository analysis
* Intelligence results
* Quality scores
* AI strategy
* Execution details
* Validation results
* Git checkpoint information

---

# Tested Repositories

| Repository      | Category          | Result |
| --------------- | ----------------- | ------ |
| LangChain       | AI Framework      | Passed |
| FastAPI         | Backend Framework | Passed |
| Cal.com         | SaaS Platform     | Passed |
| Custom Projects | Applications      | Passed |

---

# Version History

| Version | Focus                                         |
| ------- | --------------------------------------------- |
| V1      | Basic AI repository automation                |
| V2      | Repository intelligence and analysis          |
| V3      | Autonomous AI repository engineering workflow |

---

# Roadmap

| Version | Focus                                           |
| ------- | ----------------------------------------------- |
| V4      | Advanced improvement selection and intelligence |
| V5      | Multi-agent engineering workflows               |
| V6      | Autonomous software engineering platform        |

---

# Vision

RepoForge aims to become an autonomous AI engineering platform that helps developers understand, improve, and maintain complex software systems.

The goal is to reduce repetitive engineering work while improving software quality and developer productivity.


---

## AI-maintained project notes (secondary — 2026-11-13)

This section supplements the maintainer-authored README above; it does not replace or certify the original claims.

- The current source tree, runtime data and tests are the implementation source of truth. Draft PRs and roadmap items are not shipped features.
- Preserve real and maintainer-provided data. Never silently substitute synthetic or placeholder records; isolate and label test fixtures.
- Verify installation, execution, tests and claims against the exact current commit before presenting the project to recruiters, researchers or professors.
- See [MODEL_AUDIT_ROUTER.md](MODEL_AUDIT_ROUTER.md) for independent review instructions and the merge gate.


### Proposed implementation changes — not merged as of 2026-11-13

The following work is in open pull requests and must not be presented as current default-branch functionality until merged and re-tested:

- [PR #3](https://github.com/Gitcoder12/RepoForge/pull/3) proposes recovery of the canonical installable `src/repoforge` package, a `repoforge` CLI for version/help/repository validation, offline mock-provider primitives, structured logging, and stricter CI. Its branch README explicitly says the legacy autonomous `forge` command is not yet wired into the canonical CLI and that provider integrations are not yet exposed.
- [PR #5](https://github.com/Gitcoder12/RepoForge/pull/5) proposes coding/research/reviewer agents and a five-stage, human-approved prompt assembly workflow. Its worklog states that branch test/format verification is pending and that this workflow does not automatically modify repositories or certify production readiness.

Review each PR's exact head and CI before relying on these features. The original maintainer-authored README above is retained for historical continuity; claims about the scanner, quality scoring, tested repositories, and autonomous execution must be checked against the actual default-branch code before recruiters or users are told those features work.
