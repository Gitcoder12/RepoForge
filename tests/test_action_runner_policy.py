import subprocess

from action_runner import ActionRunner


def _git_repo(path, branch="feature/constitutional-policy"):
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "RepoForge Tests"], cwd=path, check=True)
    (path / "tracked.txt").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=path, check=True, capture_output=True)


def test_action_runner_blocks_unapproved_mutation(tmp_path):
    _git_repo(tmp_path)
    target = tmp_path / "tracked.txt"
    result = ActionRunner(str(tmp_path)).run([
        {"type": "modify", "file": "tracked.txt", "content": "changed"}
    ])
    assert result["status"] == "blocked"
    assert target.read_text(encoding="utf-8") == "baseline"
    assert result["errors"][0]["policy"] == "RF-06"


def test_action_runner_allows_exactly_approved_path(tmp_path):
    _git_repo(tmp_path)
    target = tmp_path / "tracked.txt"
    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "tracked.txt", "content": "approved"}],
        approved_paths={"tracked.txt"},
    )
    assert result["status"] == "completed"
    assert target.read_text(encoding="utf-8") == "approved"


def test_action_runner_blocks_entire_batch_if_one_path_is_unapproved(tmp_path):
    _git_repo(tmp_path)
    target = tmp_path / "tracked.txt"
    result = ActionRunner(str(tmp_path)).run(
        [
            {"type": "modify", "file": "tracked.txt", "content": "should-not-write"},
            {"type": "create", "file": "new.txt", "content": "not-approved"},
        ],
        approved_paths={"tracked.txt"},
    )
    assert result["status"] == "blocked"
    assert target.read_text(encoding="utf-8") == "baseline"
    assert not (tmp_path / "new.txt").exists()


def test_action_runner_preserves_dirty_user_worktree(tmp_path):
    _git_repo(tmp_path)
    user_file = tmp_path / "user-work.txt"
    user_file.write_text("keep", encoding="utf-8")
    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "tracked.txt", "content": "changed"}],
        approved_paths={"tracked.txt"},
    )
    assert result["status"] == "blocked"
    assert user_file.read_text(encoding="utf-8") == "keep"
    assert (tmp_path / "tracked.txt").read_text(encoding="utf-8") == "baseline"


def test_dry_run_previews_without_approval_or_mutation(tmp_path):
    _git_repo(tmp_path)
    target = tmp_path / "tracked.txt"
    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "tracked.txt", "content": "preview"}],
        dry_run=True,
    )
    assert result["status"] == "completed"
    assert result["executed"][0]["status"] == "dry_run"
    assert target.read_text(encoding="utf-8") == "baseline"


def test_delete_requires_explicit_separate_approval(tmp_path):
    _git_repo(tmp_path)
    target = tmp_path / "tracked.txt"
    denied = ActionRunner(str(tmp_path)).run(
        [{"type": "delete", "file": "tracked.txt"}],
        approved_paths={"tracked.txt"},
    )
    assert denied["status"] == "blocked"
    assert target.exists()

    allowed = ActionRunner(str(tmp_path)).run(
        [{"type": "delete", "file": "tracked.txt"}],
        approved_paths={"tracked.txt"},
        allow_delete=True,
    )
    assert allowed["status"] == "completed"
    assert not target.exists()
