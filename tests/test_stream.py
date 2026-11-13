import json
import threading

import pytest

from repoforge.stream import StreamEvent, StreamManager, TaskStatus


def test_task_lifecycle_and_progress() -> None:
    stream = StreamManager()
    events = []
    stream.register_callback(lambda event, task: events.append((event, task.name)))
    stream.add_task("build")
    stream.start_task("build", "starting")
    stream.update_task("build", "compiling")
    stream.complete_task("build", "done")
    stream.finish()

    assert stream.tasks["build"].status is TaskStatus.COMPLETED
    assert stream.completed_tasks == 1
    assert stream.progress == 100.0
    assert events == [
        (StreamEvent.START, "build"),
        (StreamEvent.UPDATE, "build"),
        (StreamEvent.COMPLETE, "build"),
    ]


def test_failed_and_pending_tasks_are_counted() -> None:
    stream = StreamManager()
    stream.add_task("first")
    stream.add_task("second")
    stream.start_task("first")
    stream.fail_task("first", "timeout")

    assert stream.failed_tasks == 1
    assert stream.pending_tasks == 1
    assert stream.progress == 50.0
    assert stream.summary() == "0 completed, 1 failed, 1 pending"


def test_stream_rejects_invalid_transitions() -> None:
    stream = StreamManager()
    with pytest.raises(ValueError, match="does not exist"):
        stream.start_task("missing")
    stream.add_task("task")
    with pytest.raises(ValueError, match="Only running"):
        stream.update_task("task", "not started")
    stream.start_task("task")
    stream.complete_task("task")
    with pytest.raises(ValueError, match="terminal"):
        stream.fail_task("task", "late failure")


def test_stream_snapshot_is_json_serializable(tmp_path) -> None:
    stream = StreamManager()
    stream.add_task("task", model="mock")
    stream.start_task("task")
    stream.complete_task("task", "ok")
    snapshot = stream.snapshot()
    assert json.loads(stream.to_json())["progress"] == snapshot["progress"]

    target = tmp_path / "nested" / "stream.json"
    stream.save(target)
    assert json.loads(target.read_text(encoding="utf-8"))["tasks"][0]["name"] == "task"



def test_concurrent_task_additions_have_consistent_snapshots() -> None:
    stream = StreamManager()

    def add_tasks() -> None:
        for index in range(500):
            stream.add_task(f"task-{index}")

    writer = threading.Thread(target=add_tasks)
    writer.start()
    while writer.is_alive():
        snapshot = stream.snapshot()
        statistics = snapshot["statistics"]
        assert len(snapshot["tasks"]) == snapshot["total_tasks"]
        assert (
            statistics["completed"]
            + statistics["failed"]
            + statistics["running"]
            + statistics["pending"]
            == statistics["total"]
        )
        live_statistics = stream.statistics()
        assert (
            live_statistics["completed"]
            + live_statistics["failed"]
            + live_statistics["running"]
            + live_statistics["pending"]
            == live_statistics["total"]
        )
    writer.join()

    assert stream.total_tasks == 500
