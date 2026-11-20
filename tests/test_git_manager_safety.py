import subprocess

from git_manager import GitManager


def _git_repo(path):
    subprocess.run(["git", "init", "-b", "feature/checkpoint-test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "RepoForge Tests"], cwd=path, check=True)
    (path / "tracked.txt").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=path, check=True, capture_output=True)


def test_checkpoint_records_clean_head_without_creating_commit(tmp_path):
    _git_repo(tmp_path)
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    result = GitManager(str(tmp_path)).save_state()
    after = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert result["success"]
    assert result["checkpoint"] == before == after


def test_checkpoint_refuses_dirty_tree_without_staging_user_files(tmp_path):
    _git_repo(tmp_path)
    user_file = tmp_path / "private-notes.txt"
    user_file.write_text("do not stage", encoding="utf-8")
    result = GitManager(str(tmp_path)).save_state()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout
    assert not result["success"]
    assert "dirty" in result["message"].lower()
    assert "?? private-notes.txt" in status
