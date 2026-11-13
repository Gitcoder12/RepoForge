from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from action_runner import ActionRunner


def test_create_action_writes_inside_repository(tmp_path: Path) -> None:
    runner = ActionRunner(str(tmp_path))
    result = runner.run([{"type": "create", "file": "docs/notes.md", "content": "safe"}])

    assert result["completed"] == 1
    assert (tmp_path / "docs" / "notes.md").read_text(encoding="utf-8") == "safe"


@pytest.mark.parametrize("filepath", ["../outside.txt", "/tmp/outside.txt"])
def test_write_rejects_paths_outside_repository(tmp_path: Path, filepath: str) -> None:
    runner = ActionRunner(str(tmp_path))
    result = runner.run([{"type": "create", "file": filepath, "content": "unsafe"}])

    assert result["completed"] == 0
    assert result["status"] == "partial"
    assert result["errors"]
    assert not (tmp_path.parent / "outside.txt").exists()


def test_write_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-dir"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)

    runner = ActionRunner(str(tmp_path))
    result = runner.run([{"type": "create", "file": "linked/payload.txt", "content": "unsafe"}])

    assert result["completed"] == 0
    assert result["errors"]
    assert not (outside / "payload.txt").exists()


def test_create_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "important.txt"
    target.write_text("original", encoding="utf-8")

    result = ActionRunner(str(tmp_path)).run(
        [{"type": "create", "file": "important.txt", "content": "replacement"}]
    )

    assert result["completed"] == 0
    assert target.read_text(encoding="utf-8") == "original"


def test_modify_requires_existing_file(tmp_path: Path) -> None:
    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "missing.txt", "content": "replacement"}]
    )

    assert result["completed"] == 0
    assert result["errors"]
