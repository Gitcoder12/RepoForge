# RepoForge Mastery quick start

This document describes the proposed multi-model foundation on the
`feat/repoforge-mastery-foundation` branch. It is not available from the default
branch unless the pull request is reviewed and merged.

## Install

Use Python 3.10 or newer and Git.

```bash
python -m pip install -e ".[dev,providers]"
```

Create a `.env` file in the directory where you run RepoForge, or export the
variables in your shell. Never commit the `.env` file.

## Configure providers

### OpenRouter (recommended for broad model choice)

```dotenv
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=openrouter/auto
```

Pass any model identifier supported by your OpenRouter account with
`--model`, for example a provider/model identifier from OpenRouter's model
catalog. RepoForge does not hardcode or claim to support every model in the
catalog; availability, context limits, and capabilities are determined by
OpenRouter and the selected model.

### Direct provider APIs

```dotenv
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-enabled-model

ANTHROPIC_API_KEY=your-key
ANTHROPIC_MODEL=your-enabled-model
```

### Other OpenAI-compatible gateways

For DeepSeek, Groq, LM Studio, vLLM, or another compatible endpoint:

```dotenv
REPOFORGE_API_KEY=your-key
REPOFORGE_BASE_URL=https://your-compatible-endpoint/v1
REPOFORGE_MODEL=your-model-id
```

For a local gateway that does not require authentication, the provider adapter
uses a placeholder API-key value because the SDK requires one. The SDK sends
that placeholder in its Authorization header; configure the local gateway to
ignore it if authentication is disabled.

Check configuration without printing secrets:

```bash
repoforge models
```

## Choose a repository

All repository commands accept one of:

- A local Git repository path.
- A public GitHub URL such as `https://github.com/owner/repository`.
- A short GitHub reference such as `owner/repository`.

Remote repositories are cloned into `~/.repoforge/workspaces` and reused only
when the cached clone's origin matches. Existing local directories must be Git
repositories. Private repository access depends on the Git credentials already
configured on the machine.

Inspect a repository before sending context to a model:

```bash
repoforge inspect owner/repository
repoforge inspect ./my-project
```

RepoForge sends bounded text context and excludes common secret files,
generated directories, symlinks, and large/binary files. Inspect the repository
and review the context policy before using it with third-party model APIs.

## Multi-model engineering proposal

```bash
repoforge forge owner/repository "Add robust input validation and tests" \
  --architect-provider openrouter \
  --architect-model openrouter/auto \
  --coder-provider openrouter \
  --coder-model openrouter/auto \
  --reviewer-provider anthropic \
  --reviewer-model "$ANTHROPIC_MODEL"
```

This runs the architect, coder, and reviewer roles with independently selected
providers. The result is saved under `~/.repoforge/proposals`. It does **not**
edit repository files, execute generated code, run target-repository tests,
commit, push, or open a pull request. A reviewer PASS is a model review, not
proof of correctness.

## Approval-gated single-file Turbo

```bash
repoforge turbo owner/repository src/module.py \
  "Add type hints and improve error handling" \
  --provider openrouter --model openrouter/auto
```

Turbo reads one existing file, asks the selected model for a complete
replacement, validates Python syntax when the target is a Python file, shows a
unified diff, and asks for explicit approval. On approval it creates a unique
backup and atomically replaces the file. It refuses secret files, path
traversal, symlink targets, empty responses, invalid Python syntax, and
concurrent changes to the target file.

Turbo does not automatically run the target project's tests, commit, push,
merge, or create a PR. Review the diff and run the project's real test suite
after applying a change.

## Safety and limitations

- Treat repository content and model output as untrusted.
- Do not send proprietary or sensitive repositories to a hosted provider unless
  you have permission and understand that provider's data handling terms.
- Model availability and behavior vary by provider and model.
- Multi-model review can find additional issues, but model agreement is not
  proof.
- The current `forge` command produces a proposal; it is not an autonomous
  whole-repository patch engine.
- No operation writes to GitHub or the default branch automatically.
