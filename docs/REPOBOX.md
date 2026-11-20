# RepoBox

RepoBox is RepoForge's local repository store and isolated-workspace foundation.

## Install

Install RepoForge from the repository root:

```bash
python -m pip install -e ".[dev]"
```

## Import a local repository

```bash
repobox import /path/to/local/git/repository
repobox list
```

Imports are local-only. RepoBox clones the source checkout into its own managed storage directory (by default `~/.repoforge/repobox`). It does not modify the original checkout.

The source working tree must be clean: RepoBox rejects tracked modifications and untracked files instead of silently omitting local work. Commit or stash those changes before importing. RepoBox also checks that the source HEAD remains unchanged during the import and that the managed clone starts at the observed source HEAD.

## Create an isolated task workspace

Copy the repository ID returned by `repobox import`:

```bash
repobox workspace my-project-a1b2c3d4 repair-001
```

The command creates a detached Git worktree under `~/.repoforge/repobox/workspaces/`. Make and inspect candidate changes there. The original source checkout and RepoBox's imported base clone remain separate from workspace edits.

Use `--root /path/to/repobox` before the subcommand to select a different storage directory.

## Manifest integrity and concurrency

- Manifest writes use a unique temporary file, flush the file contents, and atomically replace `manifest.json`.
- Manifest read-modify-write operations are serialized across processes with an atomic lock directory.
- Manifest records are schema-checked, including repository IDs, Git HEAD values and managed-path confinement.
- A lock that remains after a crashed process is not deleted automatically. Verify no RepoBox process is active before manually removing `.manifest.lock`.

## Current boundaries

- This is local repository inventory and Git-worktree isolation, not an OS/container sandbox.
- It does not execute repository code or tests.
- It does not automatically approve, apply or merge candidate changes into the source checkout.
- Do not treat a successful import or workspace creation as a security certification.
- RepoBox protects the original source checkout from workspace edits, but host-level isolation, quotas, workspace lifecycle management and crash recovery remain future work.
