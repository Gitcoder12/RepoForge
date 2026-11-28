# Forge: one-command repository workflow

RepoForge's `forge` command connects repository inspection, test discovery,
static validation, optional model-generated patch proposals, policy-gated
application, and post-change reporting.

## Read-only inspection (default)

```bash
repoforge forge ./repo "add focused unit tests"
```

This scans the repository, discovers likely test commands, performs static
Python validation, and prints a JSON report. It does not contact a model or
modify files.

## Generate a patch proposal

```bash
repoforge forge ./repo "add focused unit tests" --provider ollama
```

Select a provider explicitly. RepoForge sends a bounded sample of relevant
source, test, README, and manifest content to that provider to ground its patch
proposal. Obvious credential assignments are redacted and sensitive filenames
are excluded, but this is not a perfect secret scanner. Do not send confidential
repositories to a remote provider unless your organization's policy permits it;
use a local provider such as Ollama when appropriate. Remote providers may incur
charges. RepoForge does not silently switch providers or fabricate model output.

## Apply only after reviewing exact paths

```bash
repoforge forge ./repo "add focused unit tests" \
  --provider ollama --apply \
  --approve tests/test_feature.py
```

Application requires a clean Git working tree, a non-protected branch, and
approval for every exact target path. Deletions are disabled. The action runner
preflights the full batch before writing. It canonicalizes path separators,
rejects traversal and absolute/drive-qualified paths, denies symlink path
components (including internal aliases), and denies existing hard-linked file
targets so an approved repository path cannot silently mutate another hard
link. These are path-confinement safeguards, not a substitute for OS isolation
or race-free execution.

Add `--run-tests` only for repositories you trust. Target tests execute
repository-controlled code and are **not OS-sandboxed**. This command is not
a security boundary and is not a production autonomous coding guarantee.

## Report file

Use `--output forge-report.json` to save the complete machine-readable report.


## Model context boundary

The proposal prompt receives at most 16 selected text files and 36,000 source
characters. It skips common generated/dependency directories, symlinks, obvious
credential filenames, environment files, and lockfiles; it redacts common
credential-style assignments. This reduces accidental exposure but is not a
guarantee that source context contains no secrets. Review the repository and
provider policy before using a remote model.


## Apply and failure semantics

ActionRunner preflights the proposed batch and checks the clean working tree,
branch policy, and exact approved paths before writing. The filesystem writes
are not a transaction, and RepoForge does not automatically roll back a patch
if post-validation or target tests fail. A failed post-check is reported
explicitly; inspect `git diff` and revert or repair the changes yourself.
