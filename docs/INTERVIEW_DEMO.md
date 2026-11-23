# RepoForge — interview demonstration

## 30-second explanation

RepoForge is a local repository-analysis and engineering-assistance CLI. It indexes code structure, performs static validation, discovers candidate test commands, and can prepare bounded change proposals. The user remains in control of provider selection, file approval, and mutation.

It is not a one-click autonomous software factory, a security certification, or an OS sandbox.

## Five-minute walkthrough

### 1. Install and inspect the CLI

~~~bash
git clone https://github.com/Gitcoder12/RepoForge.git
cd RepoForge
python -m venv .venv
~~~

Activate the environment, then:

~~~bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
repoforge --help
repoforge version
~~~

### 2. Build a source dictionary

~~~bash
repoforge index PATH_TO_A_TRUSTED_REPOSITORY --output /tmp/repo-dictionary.json
~~~

Explain that the dictionary summarizes supported source files, symbols, imports, and local dependency relationships. Some adapters are lexical rather than full compiler parsers; skipped files and parse errors must be reviewed.

### 3. Run static validation

~~~bash
repoforge validate PATH_TO_A_TRUSTED_REPOSITORY
~~~

Static validation is the default. It does not execute the target repository's tests.

### 4. Discover the candidate test command

~~~bash
repoforge test PATH_TO_A_TRUSTED_REPOSITORY
~~~

Test discovery is not test execution. Do not run target tests from untrusted repositories: test code is repository-controlled and the current execution path is not OS-sandboxed.

### 5. Demonstrate the proposal workflow

For a trusted disposable repository, use the documented Forge preview workflow:

~~~bash
repoforge forge PATH_TO_A_TRUSTED_REPOSITORY "Inspect the project and propose one small documentation improvement"
~~~

The preview should be inspected before any mutation. A real apply requires an explicitly selected provider, a clean working tree, and exact path approval:

~~~bash
repoforge forge PATH_TO_A_TRUSTED_REPOSITORY "Improve the installation instructions" --provider PROVIDER_NAME --apply --approve README.md
~~~

The example path is illustrative. Approve only the exact path you have reviewed. Inspect the resulting Git diff immediately.

## Engineering points to explain

- **Repository indexing:** creates structured context instead of relying only on a flat file listing.
- **Validation:** checks proposed source with bounded validators before any change is accepted.
- **Explicit provider selection:** avoids silently choosing a paid model provider.
- **Path approval:** prevents the model from authorizing its own file scope.
- **Git cleanliness/checkpointing:** makes the initial repository state explicit before an apply workflow.
- **Honest execution boundary:** test execution is not an OS sandbox and must only target trusted code.

## Current development boundary

The Phase 1 safe_rsi_step transaction helper is under review in a separate pull request and is not part of the default branch until merged and retested. Do not present it as a released CLI command.

## Likely interview questions

**Does RepoForge execute arbitrary code safely?**  
No. Static validation does not execute code, but optional target-test execution runs repository-controlled code and is not OS-sandboxed. This is an explicit limitation.

**Can a model apply changes without permission?**  
The documented apply flow requires explicit provider selection, --apply, and exact approved paths. Review the actual code and report for the specific commit being demonstrated.

**What happens if a model proposes a path you did not approve?**  
The apply path should reject missing or extra path approvals. Demonstrate this with a disposable test repository and the current source/tests.

**Why not let the model decide whether its own changes are safe?**  
The engineering design separates model proposals from deterministic local validation and user-controlled scope approval.

## Before sharing with an interviewer

- Run clean installation, repoforge --help, lint, formatting, and the full test suite on the exact commit.
- Demonstrate indexing and validation on a small trusted repository.
- Demonstrate preview first; only apply on a disposable branch after explicit approval.
- Show the Git diff and the generated report.
- Explain parser coverage, test-execution limitations, and rollback limitations honestly.
- Do not describe a draft PR as part of main.
