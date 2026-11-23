import subprocess

from repoforge.action_runner import ActionRunner
from repoforge.safe_rsi import safe_rsi_step


def _git_repo(path):
    subprocess.run(
        ["git", "init", "-b", "feature/safe-rsi"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "RepoForge Tests"], cwd=path, check=True)
    (path / "baseline.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "baseline.py"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=path, check=True, capture_output=True)


def test_safe_rsi_step_defaults_to_validated_preview_without_mutation(tmp_path):
    _git_repo(tmp_path)
    report = safe_rsi_step(
        tmp_path,
        [{"type": "create", "file": "src/new_module.py", "content": "VALUE = 2\n"}],
        approved_paths={"src/new_module.py"},
    )
    assert report["status"] == "previewed"
    assert report["checkpoint"]
    assert report["dry_run"]["status"] == "completed"
    assert report["pre_validation"]["passed"] is True
    assert not (tmp_path / "src/new_module.py").exists()
    assert report["tests"]["status"] == "not_run"


def test_safe_rsi_step_applies_only_exactly_approved_python_paths(tmp_path):
    _git_repo(tmp_path)
    report = safe_rsi_step(
        tmp_path,
        [{"type": "create", "file": "src/new_module.py", "content": "VALUE = 2\n"}],
        approved_paths={"src/new_module.py"},
        apply=True,
    )
    assert report["status"] == "applied"
    assert report["post_validation"]["passed"] is True
    assert (tmp_path / "src/new_module.py").read_text(encoding="utf-8") == "VALUE = 2\n"


def test_safe_rsi_step_rejects_missing_or_extra_path_approval(tmp_path):
    _git_repo(tmp_path)
    report = safe_rsi_step(
        tmp_path,
        [{"type": "create", "file": "new.py", "content": "VALUE = 2\n"}],
        approved_paths={"other.py"},
        apply=True,
    )
    assert report["status"] == "blocked"
    assert "approval must exactly match" in report["reason"]
    assert not (tmp_path / "new.py").exists()


def test_safe_rsi_step_fails_closed_for_non_python_changes(tmp_path):
    _git_repo(tmp_path)
    report = safe_rsi_step(
        tmp_path,
        [{"type": "create", "file": "src/app.ts", "content": "export const value = 1;"}],
        approved_paths={"src/app.ts"},
        apply=True,
    )
    assert report["status"] == "blocked"
    assert "Python files only" in report["reason"]


def test_safe_rsi_step_rejects_invalid_or_flagged_python_before_apply(tmp_path):
    _git_repo(tmp_path)
    report = safe_rsi_step(
        tmp_path,
        [{"type": "create", "file": "unsafe.py", "content": "import os\nos.system('echo unsafe')\n"}],
        approved_paths={"unsafe.py"},
        apply=True,
    )
    assert report["status"] == "blocked"
    assert report["pre_validation"]["passed"] is False
    assert not (tmp_path / "unsafe.py").exists()


def test_safe_rsi_step_restores_only_approved_path_after_partial_apply(tmp_path, monkeypatch):
    _git_repo(tmp_path)
    target = tmp_path / "baseline.py"
    original = target.read_text(encoding="utf-8")

    def partial_run(self, actions, dry_run=False, **kwargs):
        if dry_run:
            return {"status": "completed", "executed": [], "errors": []}
        target.write_text(actions[0]["content"], encoding="utf-8")
        return {"status": "partial", "executed": [], "errors": [{"error": "injected failure"}]}

    monkeypatch.setattr(ActionRunner, "run", partial_run)
    report = safe_rsi_step(
        tmp_path,
        [{"type": "modify", "file": "baseline.py", "content": "VALUE = 99\n"}],
        approved_paths={"baseline.py"},
        apply=True,
    )
    assert report["status"] == "rolled_back"
    assert report["rollback"]["restored_paths"] == ["baseline.py"]
    assert target.read_text(encoding="utf-8") == original
