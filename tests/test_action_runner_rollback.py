import subprocess

from repoforge.action_runner import ActionRunner


def _git_repo(path):
    subprocess.run(["git", "init", "-b", "feature/rollback-test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "RepoForge Tests"], cwd=path, check=True)
    (path / "tracked.txt").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=path, check=True, capture_output=True)


def test_failed_batch_restores_modified_files_and_removes_created_files(tmp_path, monkeypatch):
    _git_repo(tmp_path)
    runner = ActionRunner(tmp_path)
    original_execute = runner._execute_dict_action
    calls = 0

    def fail_second_action(action, dry_run):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated disk failure")
        original_execute(action, dry_run)

    monkeypatch.setattr(runner, "_execute_dict_action", fail_second_action)
    result = runner.run(
        [
            {"type": "modify", "file": "tracked.txt", "content": "changed"},
            {"type": "create", "file": "new.txt", "content": "new"},
        ],
        approved_paths={"tracked.txt", "new.txt"},
    )

    assert result["status"] == "rolled_back"
    assert (tmp_path / "tracked.txt").read_text(encoding="utf-8") == "baseline"
    assert not (tmp_path / "new.txt").exists()
    assert result["completed"] == 0
