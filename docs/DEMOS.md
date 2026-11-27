# RepoForge demos

These examples exercise the current local mutation boundary. Use a disposable repository. The experimental HookChain selection workflow is documented in [HOOK_CHAIN.md](HOOK_CHAIN.md); it does not provide an OS-level sandbox for repository-controlled code.

## 1. Install and inspect the CLI

From the RepoForge repository root:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
python -m repoforge --help
pytest -q
```

## 2. Create a disposable target repository

Run this from a terminal. It creates a separate temporary Git repository and a non-protected working branch; it does not use or modify your real project.

```bash
python - <<'PY'
import subprocess
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="repoforge-demo-"))
subprocess.run(["git", "init", "-b", "demo/repoforge"], cwd=root, check=True)
subprocess.run(["git", "config", "user.name", "RepoForge Demo"], cwd=root, check=True)
subprocess.run(["git", "config", "user.email", "demo@example.invalid"], cwd=root, check=True)
(root / "README.md").write_text("# Disposable RepoForge target\n", encoding="utf-8")
subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
subprocess.run(["git", "commit", "-m", "Create disposable demo target"], cwd=root, check=True)
print(root)
PY
```

Copy the printed path for the next command.

## 3. Preview, then explicitly approve one file

Save this as `examples/approved_write_demo.py` in the RepoForge checkout:

```python
import sys
from pathlib import Path

from repoforge.action_runner import ActionRunner

target = Path(sys.argv[1]).resolve()
actions = [
    {
        "type": "create",
        "file": "docs/REPOFORGE_DEMO.md",
        "content": "# RepoForge demo\n\nCreated only after explicit path approval.\n",
    }
]

runner = ActionRunner(target)

# Preview only: no repository write occurs.
preview = runner.run(actions, dry_run=True)
print("preview:", preview["status"])

# Explicit consent is represented by approving this exact relative path.
# The target must be a clean Git repository on a non-protected branch.
result = runner.run(
    actions,
    dry_run=False,
    approved_paths={"docs/REPOFORGE_DEMO.md"},
)
print("apply:", result["status"])
print("completed:", result["completed"])
print("errors:", result["errors"])
```

Run it with the temporary path printed in step 2:

```bash
python examples/approved_write_demo.py /path/to/repoforge-demo-XXXX
```

On Windows, pass the printed Windows path. Then inspect the target:

```bash
git -C /path/to/repoforge-demo-XXXX status --short
git -C /path/to/repoforge-demo-XXXX diff
```

The demo creates one new file only. It does not modify existing files, delete files, commit changes, or touch the RepoForge checkout. The policy rejects dirty targets, protected branches, path traversal, unapproved paths, and deletes without a separate delete approval.

## Current boundary

This is a local `ActionRunner` example rather than the multi-repository HookChain. The installable CLI's HookChain is still an experimental inspect/select flow and only applies create-only safe repairs. Test execution against untrusted repositories is not sandboxed. Do not point this demo at valuable working trees.
