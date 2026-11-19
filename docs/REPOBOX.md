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

## Create an isolated task workspace

Copy the repository ID returned by `repobox import`:

```bash
repobox workspace my-project-a1b2c3d4 repair-001
```

The command creates a detached Git worktree under `~/.repoforge/repobox/workspaces/`. Make and inspect candidate changes there. The original source checkout and RepoBox's imported base clone remain separate from workspace edits.

Use `--root /path/to/repobox` before the subcommand to select a different storage directory.

## Current boundaries

- This is local repository inventory and Git-worktree isolation, not an OS/container sandbox.
- It does not execute repository code or tests.
- It does not automatically approve, apply or merge candidate changes into the source checkout.
- Do not treat a successful import or workspace creation as a security certification.
- The first version is single-user local storage; concurrent writers to one RepoBox manifest are not coordinated.
