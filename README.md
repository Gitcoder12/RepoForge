# RepoForge


## Current Status / Current Version

**Development — no verified release tag recorded**

**Implemented according to current documentation:** repository scanning and analysis; quality/difficulty scoring; planning/orchestration and action execution pipeline; validation, Git checkpointing and reporting; TestForge test-command discovery; Blacksmith bounded create-only repair workflow; Megazords repository comparison; RepoDictionary structural indexing for a broad set of languages through built-in and custom adapters.

**Known limitations:** TestForge execution is not OS-sandboxed and must not be used on untrusted repositories. Blacksmith does not implement arbitrary semantic code repair. A documented pipeline or example output is not proof of successful end-to-end execution on arbitrary repositories.

**Verification still required:** clean installation, actual test results, before/after diffs, rollback behavior and reproducible external-repository demonstrations.


## Maintainer status snapshot — 2026-11-22

**Default branch:** `main` at `ab3e7912055243d991b9eb91687e7bb171153ca6`. **Project status:** active development prototype; no verified release tag recorded.

This snapshot is authoritative for current project status. Older example output, roadmap entries and feature descriptions elsewhere in this README are not proof that the corresponding workflow is available or has passed end-to-end validation on the current default branch.

- The current documented mainline includes repository inspection/health signals, TestForge command discovery, bounded Blacksmith hygiene repairs and Megazords comparison. TestForge execution is **not OS-sandboxed**; do not execute untrusted repository code.
- RepoRank/UpgradeForge, RepoBox, RAG/FastMCP, Resource Governor, Resources Hub and Global Repository Intelligence work remains in open PRs. These are not mainline features until merged and re-tested.
- **Open PR snapshot:** 13 PRs were open at audit time. #30 (System Health), #28 (RAG/FastMCP) and #26 (UpgradeForge) had green recorded CI; #30 is the strongest non-draft candidate from this snapshot. #34 (Resources Hub) fails lint due to undefined `timezone`; #33 (Resource Governor) fails Ruff formatting; #31 (Global Repository Intelligence) fails Ruff checks. #32 depends on #31. #5 has unresolved security/architecture findings, and #20 requires further mergeability/CI review.
- **Verification status:** this audit inspected PR metadata, selected diffs, review threads and recorded CI jobs. It did not execute every feature against arbitrary external repositories. Historical “tested repositories” and sample reports in this README must be backed by reproducible logs before being used as current evidence.

See [docs/MAINTAINER_STATUS_2026-11-22.md](docs/MAINTAINER_STATUS_2026-11-22.md) for the audit snapshot, PR triage, known failures, branch policy and next steps. Recheck live GitHub state before merging because CI and branch heads can change.


## Commands — copy, paste, run

RepoForge is a local CLI. Open a terminal in the repository folder and use these commands in order.

### 1. Install (Windows PowerShell)

Python 3.10 or newer is supported. This command uses your active `python` installation (your machine currently reports Python 3.13).

```powershell
git clone https://github.com/Gitcoder12/RepoForge.git
cd RepoForge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Install (macOS / Linux)

```bash
git clone https://github.com/Gitcoder12/RepoForge.git
cd RepoForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 2. See all commands

```bash
repoforge --help
repoforge version
```

### Build a repository dictionary

```powershell
repoforge index ..\flask
```

This writes `repo_dictionary.json` into the target repository. The index records supported source files, symbols, imports, and resolvable local dependencies. Built-in adapters cover Python, JavaScript/TypeScript, Go, Java, Kotlin, C#, C/C++, Rust, Ruby, PHP, Swift, Dart, Scala/Groovy, shell, SQL, Lua, Elixir/Erlang, Haskell, R, Julia, Perl, PowerShell, Terraform/HCL, GraphQL, Protocol Buffers, Objective-C, F#, Visual Basic, OCaml, Clojure, Vue, Svelte, and Elm. Python uses the standard-library AST; several other language adapters use conservative lexical patterns, not full compiler parsers. They are structural hints and may miss constructs or report false positives. Indexing does not execute source code or modify source files. Use `--output <path>` to choose another destination.

Adapters are extensible from Python code with the public `LanguageAdapter` and `register_language_adapter()` API. A regex adapter declares file suffixes, symbol patterns with a named `name` group, and import patterns with a named `module` group. A custom extractor callback can integrate a dedicated parser; extractors must remain non-executing. See `tests/test_dictionary_universal.py` for a minimal registration example.

Forge checks an existing dictionary against the current source-file inventory before reusing it. If it is missing or stale, Forge builds a fresh in-memory index for that run instead of silently trusting old metadata. The index guides file and symbol discovery; Forge must still inspect the actual source before proposing a patch.

### 3. Safely inspect a repository (read-only)

```bash
repoforge blacksmith ../ARK
repoforge validate ../ARK
```

### 4. Discover tests without running them

```bash
repoforge test ../ARK
```

This prints detected test commands; it does not execute them by default.

### 5. Preview the integrated Forge workflow (read-only)

```bash
repoforge forge ../ARK "Review the repository structure, identify risks, and propose prioritized improvements"
```

No provider is selected and no files are changed in this default preview.

### 6. Ask a model for a proposal (still do not apply it)

Configure a provider key in your environment first, then check configuration:

```bash
repoforge providers
repoforge forge ../ARK "Propose a small documentation improvement" --provider deepseek
```

Provider names and credentials depend on your setup. Model requests may incur charges. Review the returned proposed paths and changes before considering an apply.

### 7. Apply only explicitly approved paths

Only do this in a disposable test repository or a clean Git branch, after reviewing the proposal. Replace the example path with the exact repository-relative path shown in the proposal:

```bash
repoforge forge ../ARK "Improve the installation instructions" --provider deepseek --apply --approve README.md
```

Repeat `--approve PATH` for each exact path you authorize. Forge requires explicit apply approval and a clean working tree. Check the diff immediately afterwards:

```bash
git -C ../ARK status --short
git -C ../ARK diff
```

### 8. Compare model endpoints

```bash
repoforge model-lab --catalog
repoforge model-lab --target deepseek:deepseek-flash --output model-lab.json
```

### 9. Run RepoForge's own tests

```bash
pytest -q
```

**Important safety boundary:** TestForge's `--execute` and Forge's `--run-tests` execute target-repository test code. Execution is not OS-sandboxed. Do not run tests from untrusted repositories. Start with the read-only commands above; do not use `--apply` on ARK or another important working tree during your first test.

---

## Contributor entry point

Start with [START_HERE.md](START_HERE.md) for the canonical source map and
safe contributor workflow.

## Model Lab

Compare explicitly selected model endpoints on a small deterministic smoke
suite. See [docs/MODEL_LAB.md](docs/MODEL_LAB.md).

```bash
repoforge model-lab --catalog
repoforge model-lab --target openai:gpt-6.2-sol --target deepseek:deepseek-flash
```

This suite is not a general model ranking or a safety certification. Remote
models may incur provider charges; no provider is selected or switched
automatically.

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

## RepoRank & UpgradeForge — development branch

RepoRank provides a transparent hygiene baseline. UpgradeForge turns missing engineering signals into selectable improvement paths rather than limiting RepoForge to repairs.

```bash
# Inspect current RepoRank and see all recommended upgrade paths
repoforge blacksmith ./your-repository

# Generate a focused upgrade plan
repoforge upgrade ./your-repository --profile security
repoforge upgrade ./your-repository --profile quality

# Select exact recommendations for a review plan
repoforge upgrade ./your-repository --select tests-real,ci-pipeline
```

Available profiles: `foundation`, `security`, `quality`, `delivery`, `maintainability`, and `all`. Each recommendation includes evidence, impact, effort, risk, implementation guidance and verification criteria. The score points shown are the maximum hygiene points associated with missing signals—not guaranteed quality gains.

UpgradeForge is recommendation-only in this iteration. It does not invent tests, choose a license, overwrite files, delete files, execute target code or claim that a plan has been applied. Existing safe create-only `.gitignore` repair remains separate. Review and approve project-specific work before implementation.
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

## Running from VS Code

Open the integrated terminal at the repository root and follow the single [Commands guide](#commands--copy-paste-run) above. It contains the installation and usage commands for Windows, macOS and Linux.

---

---

# Usage

Use the central [Commands guide](#commands--copy-paste-run) for the current CLI entry points and examples.

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


---

## Comparison with Existing Open-Source Projects

RepoForge is documented as a repository-engineering platform combining repository analysis, bounded improvement workflows, validation, Git checkpoints and reports. Its Blacksmith module previews/applies limited repairs, while Megazords compares local repositories for complementary capabilities. The following projects cover adjacent coding-agent and code-quality workflows.

| Project | Established focus | Relationship to RepoForge |
|---|---|---|
| [OpenHands](https://github.com/All-Hands-AI/OpenHands) | General-purpose AI software-development agent that can work across repositories and tools | Broader autonomous software-engineering agent; RepoForge's stated distinction is a structured repository-health and bounded-change workflow with explicit before/after reporting. |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | Agent framework for resolving software-engineering issues in repositories | Focuses on issue-driven coding tasks; RepoForge aims to cover repository inspection, quality signals and controlled maintenance as well as selected changes. |
| [Aider](https://github.com/Aider-AI/aider) | AI pair-programming in local Git repositories | A mature interactive coding assistant; RepoForge's intended value is a repeatable audit/repair/validation pipeline rather than conversational code editing alone. |
| [Semgrep](https://github.com/semgrep/semgrep) | Static analysis and rule-based code security scanning | Deeper specialist static analysis; RepoForge should integrate or complement such tools rather than claim to replace their analysis depth. |

### Where RepoForge is different
- **Repository-first workflow:** scanning, health signals, complexity estimates, planning, bounded action, validation and reporting are presented as one lifecycle.
- **Approval-oriented repair:** Blacksmith's current scope is deliberately narrow and supports preview before apply rather than unrestricted code rewriting.
- **Portfolio composition analysis:** Megazords compares multiple local repositories for complementary capabilities and integration risks, not just one-repo code completion.

### Where established projects are stronger
OpenHands, SWE-agent and Aider have more mature agent workflows and ecosystems; Semgrep has deeper static-analysis rules. RepoForge's current README explicitly states that arbitrary semantic repair is not implemented and that TestForge execution is not sandboxed. Do not describe it as a secure autonomous engineer without stronger isolation and validation.

### Evidence and limitations
Publish reproducible before/after metrics, exact tools and versions, test outcomes, rollback behavior and repair acceptance rates. Keep heuristic RepoRank distinct from measured code quality. Require human approval for changes and OS-level isolation before executing untrusted tests. This is an architecture comparison, not a coding-agent benchmark.


## Demos

Run the isolated approved-write example from a disposable Git repository: [docs/DEMOS.md](docs/DEMOS.md). The current example demonstrates the local ActionRunner boundary, not the planned autonomous cross-repository hook/chain workflow.
