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

Select a provider explicitly. Remote providers may incur charges. RepoForge
does not silently switch providers or fabricate model output.

## Apply only after reviewing exact paths

```bash
repoforge forge ./repo "add focused unit tests" \
  --provider ollama --apply \
  --approve tests/test_feature.py
```

Application requires a clean Git working tree, a non-protected branch, and
approval for every exact target path. Deletions are disabled. The action runner
preflights the full batch before writing. A blocked action batch is not applied.

Add `--run-tests` only for repositories you trust. Target tests execute
repository-controlled code and are **not OS-sandboxed**. This command is not
a security boundary and is not a production autonomous coding guarantee.

## Report file

Use `--output forge-report.json` to save the complete machine-readable report.
