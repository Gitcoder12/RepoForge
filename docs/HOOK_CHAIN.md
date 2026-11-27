# HookChain — multi-repository inspection and selection board

HookChain connects the existing repository tools into one reviewable run:

1. **Blacksmith** inventories each local repository and produces RepoRank plus safe and review-required repair proposals.
2. **LangFix** optionally scans individual source files across registered languages. It runs as a separate CLI process, preview-only, with its cache redirected to a temporary working directory.
3. **UpgradeForge** contributes a ranked list of repository-level improvement recommendations.
4. **Megazords** compares two or more repositories and produces heuristic integration hypotheses.
5. **Selection board** gathers repair, upgrade, and complement IDs. The selected list is written into the JSON report.
6. **Apply-safe** applies only explicitly selected create-if-absent repairs. Upgrade recommendations and Megazord pairings remain review-only.

## Run it

Inspect one repository:

~~~bash
repoforge chain ./my-repo
~~~

Inspect several different repository types and compare them:

~~~bash
repoforge chain ./frontend ./api ./model-lab ./rust-tool --top 20
~~~

Enable the optional LangFix bridge after installing LangFix:

~~~bash
python -m pip install -e /path/to/LangFix
repoforge chain ./frontend ./api ./rust-tool --with-langfix
~~~

Show the board and select every safe repair:

~~~bash
repoforge chain ./rust-tool --select safe
~~~

Preview the selected IDs without writing:

~~~bash
repoforge chain ./rust-tool --select safe --output ./chain-report.json
~~~

Apply selected safe repairs:

~~~bash
repoforge chain ./rust-tool --select safe --apply-safe --output ./chain-report.json
~~~

Choose rows interactively:

~~~bash
repoforge chain ./frontend ./api --interactive
~~~

The option --select all checks every visible item, but --apply-safe still applies only items explicitly classified as safe create-only repairs. The option --select safe selects only those safe repairs. Row numbers and exact item IDs are also accepted.

## Rust support

Blacksmith already counts .rs source files. When a repository contains Rust and has no .gitignore, its create-only repair proposal includes Rust build-output rules:

- /target/
- **/*.rs.bk

It intentionally does not ignore Cargo.lock, because application repositories commonly commit the lockfile for reproducible builds. Existing .gitignore files are never overwritten.

LangFix's Rust adapter validates source syntax with rustfmt and can propose formatting through a temporary file. This is not equivalent to cargo check, dependency resolution, type checking, or running the project's tests.

## Lifecycle hooks

Applications embedding HookChain can register trusted in-process callbacks:

~~~python
from repoforge.chain import HookChain

chain = HookChain()
chain.register_hook(
    "repository.inspect.completed",
    lambda event: print("Inspected:", event["repository"]),
)
report = chain.inspect(["./repo-a", "./repo-b"], with_langfix=True)
~~~

Supported events are listed in HookChain.EVENTS. Callbacks receive event metadata; they are not imported from, or loaded out of, target repositories. Hook failures are recorded in hook_trace and do not cause a repository mutation.

## Safety boundary

- Repository files are inspected statically; target build scripts, project tests, and repository-defined hooks are not executed by HookChain.
- The LangFix bridge never passes --fix; it scans with --json and uses a temporary working directory for its cache.
- Optional language validators such as rustfmt, node --check, gofmt, and javac are parsers/compilers, not sandboxed security boundaries. Do not interpret this workflow as executing untrusted application tests safely.
- Only selected create-if-absent repairs can be applied by this first implementation. No overwrites, deletes, package installs, or automatic project-specific CI/test generation are performed.
- UpgradeForge options and Megazord complements are proposals, not executable actions.
- The filesystem operation is not a transaction across multiple repositories. Inspect the JSON outcomes and version-control diff after application.
- Use disposable clones or forks for first-time testing.

## External repository testing

The RepoForge CI external-clone job checks out public Rust, Go, Python, JavaScript/TypeScript, and C++ repositories into disposable runner directories. It runs static inspections and the preview-only LangFix scan, verifies the target checkouts are clean, then creates a second local throwaway clone of the Rust fixture and tests the approved Rust-aware .gitignore create-only repair there. It does not push to or alter upstream repositories.
