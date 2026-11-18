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

## TestForge — fast test discovery

TestForge detects conventional test entry points across Python, JavaScript/TypeScript, Go, Rust, Java, and .NET. It prints a test plan without executing repository code by default.

Preview the detected commands:

```bash
repoforge test .
```

Explicitly execute the detected commands for a repository you trust:

```bash
repoforge test . --execute --timeout 120
```

Execution is **not sandboxed**. Tests can run arbitrary repository-controlled code; TestForge removes common credential environment variables, uses argument arrays instead of a shell, captures bounded output, and enforces a timeout, but it does not provide OS-level isolation or network denial. Do not run untrusted repositories with `--execute`. A container-backed isolated runner is a separate future milestone.

## Blacksmith & Megazords

**Blacksmith** audits a local repository, reports a transparent before/after RepoRank, and previews or applies safe create-only repairs.

```bash
repoforge blacksmith ../your-repository
repoforge blacksmith ../your-repository --apply
```

**Megazords** compares multiple local repositories and suggests complementary combinations with integration patterns and risks—without merging or changing them.

```bash
repoforge megazords ../ARK ../Overdrive ../Chaos-Control
```

The current Blacksmith repair adapter is intentionally narrow; arbitrary semantic code repair is not yet implemented. See [docs/BLACKSMITH_MEGazords.md](docs/BLACKSMITH_MEGazords.md) for scoring, safety boundaries and limitations.

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

---

## Engineering Audit & Handover — 2026-11-17

**Reviewed commit:** `7fb348b7f0fcde7032ba355d46adc7d5722d11b5` (`main`). Static inspection covered `pipeline.py` and `action_runner.py`; tests were not executed.

### Confirmed findings
- `ActionRunner` accepts `create`, `modify`, and `delete` actions. The delete path is an available destructive capability and must remain behind explicit, reviewable authorization; a dry-run default alone is not a sufficient production safety boundary.
- `RepoForgePipeline.run()` attempts a Git checkpoint, but if checkpoint creation fails it logs a warning and continues toward action execution. This weakens the stated rollback/safety guarantee.
- When non-dry-run validation fails, the pipeline calls rollback; the inspected path does not establish that rollback itself is guaranteed to succeed or that the repository is restored byte-for-byte.
- The action runner contains repository-root path confinement checks, which are valuable safeguards; retain and test them.

### Next actions
1. Make checkpoint failure a hard stop for every write-capable run.
2. Require explicit approval for destructive actions and default to deny deletion; log the exact target and obtain a fresh confirmation.
3. Test traversal/symlink escapes, dry-run behavior, checkpoint failure, validator failure, rollback failure, and partial action errors.

**Verification status:** static source inspection only; full test suite, live model workflow, rollback behavior, and end-to-end execution remain unverified.


---

## Real model provider runtime — development PR

The installable `src/repoforge` package now has an explicit OpenAI-compatible provider runtime for DeepSeek, OpenAI, OpenRouter, Groq, and a local Ollama endpoint. The DeepSeek default is `deepseek-flash`; the Groq default is `openai/gpt-oss-120b`. Both were checked against their providers' current model documentation on 2026-11-17.

Install the provider SDK:

```bash
pip install -e ".[providers]"
```

Configure the matching environment variable (for example, `DEEPSEEK_API_KEY`) and inspect readiness without displaying credential values:

```bash
repoforge providers
```

Send a single prompt to an explicitly selected provider:

```bash
repoforge generate "Review this Python function for correctness and performance" --provider deepseek
```

Use `--model`, `--timeout`, and `--max-tokens` to control the request. For DeepSeek's higher-capability V4-Pro model, select `--model deepseek-v4-pro` explicitly. Provider quota exhaustion, authentication errors, timeouts, and connection failures are reported explicitly. SDK retries are disabled, and RepoForge does not silently substitute mock output or switch to another paid provider. Choose another provider deliberately with `--provider`.

The CLI builds and enables the selected adapter through `AIOrchestrator`, so the same explicit provider-selection contract is available to programmatic orchestration. This is still a single-request provider runtime, not yet the autonomous repository-editing `forge` workflow. It must pass CI and review before it is treated as part of the released default branch.


## Explicit standby model routing

Use an explicitly configured primary and ordered standby providers. Transient connection, timeout and unusable-response failures may trigger standby. Authentication/configuration/request failures stop; quota fallback is opt-in because it can incur extra cost. No implicit mock fallback is used.

```bash
repoforge generate "Review this patch" --provider deepseek --standby openai --standby groq
repoforge generate "Review this patch" --route-config configs/model_failover.json
```

See `configs/model_failover.json` for the sample route policy. Standby routing is not a guarantee that different models are semantically equivalent; quality checks, cost budgets and data-residency rules remain operator responsibilities.

---

## Examples Used
- Repairing a failing software repository like a blacksmith restoring a machine
- Comparing repository health before and after a bounded repair
- Combining complementary repositories into a Megazord-style system
