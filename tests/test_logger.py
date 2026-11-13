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



def test_logger_close_preserves_handlers_owned_by_host_application() -> None:
    import io
    import logging

    host_logger = logging.getLogger("RepoForge")
    original_level = host_logger.level
    host_handler_stream = io.StringIO()
    host_handler = logging.StreamHandler(host_handler_stream)
    host_logger.addHandler(host_handler)
    host_logger.setLevel(logging.INFO)
    repo_logger = RepoForgeLogger(name="RepoForge", console=True)

    try:
        repo_logger.info("TEST", "instance message")
        repo_logger.close()
        host_logger.info("host handler remains connected")
        assert host_handler in host_logger.handlers
        assert "host handler remains connected" in host_handler_stream.getvalue()
    finally:
        repo_logger.close()
        host_logger.removeHandler(host_handler)
        host_handler.close()
        host_logger.setLevel(original_level)
