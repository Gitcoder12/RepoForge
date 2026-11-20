import subprocess

from policy_engine import PolicyEngine


def _git_repo(path, branch="feature/policy-test"):
    subprocess.run(
        ["git", "init", "-b", branch], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"], cwd=path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "RepoForge Tests"], cwd=path, check=True
    )
    (path / "tracked.txt").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"], cwd=path, check=True, capture_output=True
    )


def test_dirty_worktree_is_denied_without_staging_user_changes(tmp_path):
    _git_repo(tmp_path)
    (tmp_path / "user.txt").write_text("keep me", encoding="utf-8")
    result = PolicyEngine(tmp_path).check_repository()
    assert not result.allowed
    assert result.rule_id == "RF-02"
    assert (tmp_path / "user.txt").read_text(encoding="utf-8") == "keep me"


def test_protected_branch_is_denied(tmp_path):
    _git_repo(tmp_path, branch="main")
    result = PolicyEngine(tmp_path).check_repository()
    assert not result.allowed
    assert result.rule_id == "RF-03"


def test_exact_path_approval_required_for_mutation():
    policy = PolicyEngine(".")
    action = {"type": "modify", "file": "src/example.py", "content": "pass"}
    assert not policy.evaluate_action(action).allowed
    assert policy.evaluate_action(action, approved_paths={"src/example.py"}).allowed


def test_delete_requires_separate_approval():
    policy = PolicyEngine(".")
    action = {"type": "delete", "file": "old.py"}
    assert not policy.evaluate_action(action, approved_paths={"old.py"}).allowed
    assert policy.evaluate_action(
        action, approved_paths={"old.py"}, allow_delete=True
    ).allowed


def test_absolute_and_parent_traversal_paths_are_denied():
    policy = PolicyEngine(".")
    assert not policy.evaluate_action({"type": "modify", "file": "../secret"}).allowed
    assert not policy.evaluate_action({"type": "modify", "file": "/tmp/secret"}).allowed
