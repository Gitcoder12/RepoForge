from pathlib import Path

from repoforge.logger import RepoForgeLogger


def test_logger_writes_metadata_and_execution_id(tmp_path: Path) -> None:
    logger = RepoForgeLogger(log_directory=tmp_path, console=False, file=True)
    logger.set_execution_id("run-123")
    logger.info("TEST", "hello", count=2)
    logger.close()

    output = (tmp_path / "repoforge.log").read_text(encoding="utf-8")
    assert "TEST" in output
    assert "hello" in output
    assert "run-123" in output
    assert '"count": 2' in output


def test_logger_timer_records_elapsed_time(tmp_path: Path) -> None:
    logger = RepoForgeLogger(log_directory=tmp_path, console=False, file=True)
    with logger.timer("TEST", "operation"):
        pass
    logger.close()

    output = (tmp_path / "repoforge.log").read_text(encoding="utf-8")
    assert "operation completed" in output
    assert "elapsed_seconds" in output
