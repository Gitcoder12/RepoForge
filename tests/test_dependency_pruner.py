from pathlib import Path
import pytest
from repoforge.dependency_pruner import prune_requirements, write_pruned_requirements

def test_pruner_retains_used_and_unknown_dependencies(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "requests>=2\npyyaml>=6\nunknown-plugin>=1\n", encoding="utf-8"
    )
    (tmp_path / "app.py").write_text("import requests\nimport yaml\n", encoding="utf-8")
    result = prune_requirements(tmp_path)
    assert result["retained"] == ["requests>=2", "pyyaml>=6", "unknown-plugin>=1"]
    assert result["removal_candidates"] == []

def test_pruner_marks_unused_known_dependencies_as_candidates(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "requests>=2\npyyaml>=6\n", encoding="utf-8"
    )
    (tmp_path / "app.py").write_text("import requests\n", encoding="utf-8")
    result = prune_requirements(tmp_path)
    assert result["retained"] == ["requests>=2"]
    assert result["removal_candidates"] == ["pyyaml>=6"]

def test_pruner_keeps_everything_when_dynamic_imports_exist(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("requests>=2\npyyaml>=6\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("import importlib\nimportlib.import_module('yaml')\n", encoding="utf-8")
    result = prune_requirements(tmp_path)
    assert result["dynamic_imports_detected"]
    assert result["retained"] == ["requests>=2", "pyyaml>=6"]
    assert not result["removal_candidates"]

def test_pruner_rejects_local_and_url_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("-e ../local-package\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        prune_requirements(tmp_path)

def test_writer_emits_candidate_manifest(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("import requests\n", encoding="utf-8")
    result = write_pruned_requirements(tmp_path)
    assert result["output"] == "requirements.pruned.txt"
    assert (tmp_path / "requirements.pruned.txt").read_text() == "requests>=2\n"


def test_pruner_reads_pep621_pyproject_runtime_dependencies(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\\ndependencies = ["requests>=2", "pyyaml>=6"]\\n',
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text("import requests\\nimport yaml\\n", encoding="utf-8")
    result = prune_requirements(tmp_path, manifest="pyproject.toml")
    assert result["retained"] == ["requests>=2", "pyyaml>=6"]

def test_pruner_refuses_requirements_includes(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("-r base.txt\\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        prune_requirements(tmp_path)
