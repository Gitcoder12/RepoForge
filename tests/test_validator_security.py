import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.validator import ThreatVisitor, Validator


def test_threat_visitor_handles_nested_attribute_calls() -> None:
    import ast

    tree = ast.parse("os.path.join('a', 'b')\nsubprocess.run(['echo', 'ok'])")
    visitor = ThreatVisitor()

    visitor.visit(tree)

    assert any("subprocess.run" in item for item in visitor.threats)


def test_validator_rejects_path_traversal(tmp_path: Path) -> None:
    validator = Validator(str(tmp_path))

    with pytest.raises(ValueError, match="escapes repository root"):
        validator._resolve_target("../outside.py")


def test_validator_fails_closed_on_syntax_error(tmp_path: Path) -> None:
    source = tmp_path / "broken.py"
    source.write_text("def broken(:\n", encoding="utf-8")

    result = Validator(str(tmp_path))._check_syntax(source)

    assert result["passed"] is False
    assert "error" in result



def test_validator_scan_rejects_symlink_escape(tmp_path: Path) -> None:
    import asyncio

    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')\n", encoding="utf-8")
    (repository / "escape.py").symlink_to(outside)

    result = asyncio.run(Validator(str(repository)).validate())

    assert result["passed"] is False
    assert result["reason"] == "invalid_paths"
    assert result["invalid_paths"][0]["file"] == "escape.py"
