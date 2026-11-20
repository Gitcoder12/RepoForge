from repoforge.sentinel import scan_repository


def test_reports_dangerous_code_patterns_without_executing_them(tmp_path):
    source = tmp_path / "app.py"
    source.write_text(
        "eval(user_input)\n"
        "subprocess.run(command, shell=True)\n"
        "pickle.loads(payload)\n"
        "yaml.load(document)\n",
        encoding="utf-8",
    )
    report = scan_repository(tmp_path)
    assert report.files_scanned == 1
    assert {item.rule_id for item in report.findings} == {
        "RF-SEN-001", "RF-SEN-002", "RF-SEN-004", "RF-SEN-005"
    }


def test_ignores_virtual_environment_and_symlinked_files(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "ignored.py").write_text("eval(x)", encoding="utf-8")
    real = tmp_path / "real.py"
    real.write_text("print('safe')", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(real)
    except OSError:
        pass
    report = scan_repository(tmp_path)
    assert report.files_scanned == 1
    assert not report.findings


def test_non_repository_directory_is_scannable_and_empty_is_valid(tmp_path):
    report = scan_repository(tmp_path)
    assert report.files_scanned == 0
    assert report.findings == ()


def test_invalid_root_and_file_limit_are_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        scan_repository(tmp_path / "missing")
    with pytest.raises(ValueError):
        scan_repository(tmp_path, max_files=0)


def test_large_files_are_skipped(tmp_path):
    path = tmp_path / "large.py"
    path.write_text("x" * 1_000_001, encoding="utf-8")
    report = scan_repository(tmp_path)
    assert report.files_scanned == 0
    assert report.files_skipped == 1


def test_scan_limits_bound_work_and_report_truncation(tmp_path):
    (tmp_path / "a.py").write_text("print('a')", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')", encoding="utf-8")
    report = scan_repository(tmp_path, max_files=1)
    assert report.files_scanned == 1
    assert report.truncated is True


def test_total_byte_budget_stops_scanning(tmp_path):
    (tmp_path / "a.py").write_text("x" * 100, encoding="utf-8")
    (tmp_path / "b.py").write_text("y" * 100, encoding="utf-8")
    report = scan_repository(tmp_path, max_total_bytes=150)
    assert report.bytes_scanned <= 150
    assert report.truncated is True


def test_cli_sentinel_command_returns_json(tmp_path):
    from typer.testing import CliRunner

    from repoforge.cli import app

    (tmp_path / "app.py").write_text("eval(user_input)", encoding="utf-8")
    result = CliRunner().invoke(app, ["sentinel", str(tmp_path)])
    assert result.exit_code == 0
    assert '"RF-SEN-001"' in result.stdout
