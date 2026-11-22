"""Tests for the mixed-language RepoDictionary indexer and CLI."""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from repoforge.cli import app
from repoforge.dictionary import CodebaseIndexer


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_indexes_python_typescript_and_go_symbols_and_local_dependencies(tmp_path) -> None:
    app_source = "import os\nfrom helpers import greet\n\nclass App:\n    pass\n\ndef main():\n    greet()\n"
    _write(tmp_path / "helpers.py", "def greet(name: str = 'world'):\n    return name\n")
    _write(
        tmp_path / "src/index.ts",
        'import { helper } from "./helper";\nexport class Router {}\n'
        "export const makeRouter = () => new Router();\nexport function start() {}\n",
    )
    _write(tmp_path / "src/helper.ts", "export function helper() { return 1; }\n")
    _write(tmp_path / "go.mod", "module example.com/demo\n\ngo 1.22\n")
    _write(
        tmp_path / "cmd/main.go",
        'package main\n\nimport (\n    "fmt"\n    "example.com/demo/internal/util"\n)\n'
        'const AppName = "RepoForge"\nfunc main() { fmt.Println(util.Lookup()) }\n',
    )
    _write(
        tmp_path / "internal/util/util.go",
        'package util\n\ntype Config struct {}\nfunc Lookup() string { return "ok" }\n',
    )

    index = CodebaseIndexer(tmp_path).build()

    assert index["languages"] == {"go": 2, "python": 2, "typescript": 2}
    files = {item["path"]: item for item in index["files"]}
    python_kinds = {(item["kind"], item["name"]) for item in files["app.py"]["symbols"]}
    assert ("class", "App") in python_kinds
    assert ("function", "main") in python_kinds
    assert ("import", "greet") in python_kinds

    typescript_kinds = {(item["kind"], item["name"]) for item in files["src/index.ts"]["symbols"]}
    assert ("class", "Router") in typescript_kinds
    assert ("constant", "makeRouter") in typescript_kinds
    assert ("function", "start") in typescript_kinds

    go_kinds = {(item["kind"], item["name"]) for item in files["cmd/main.go"]["symbols"]}
    assert ("function", "main") in go_kinds
    assert ("constant", "AppName") in go_kinds
    assert ("type", "Config") in {
        (symbol["kind"], symbol["name"]) for symbol in files["internal/util/util.go"]["symbols"]
    }

    assert index["dependencies"]["app.py"] == ["helpers.py"]
    assert index["dependencies"]["src/index.ts"] == ["src/helper.ts"]
    assert index["dependencies"]["cmd/main.go"] == ["internal/util/util.go"]
    assert index["summary"]["dependency_edges"] == 3


def test_index_records_python_syntax_errors_without_crashing(tmp_path) -> None:
    _write(tmp_path / "broken.py", "def unfinished(:\n    pass\n")

    index = CodebaseIndexer(tmp_path).build()

    assert index["summary"]["parse_errors"] == 1
    assert index["files"][0]["parse_error"].startswith("line 1:")
    assert index["files"][0]["symbols"] == []


def test_index_skips_generated_directories_and_respects_file_limit(tmp_path) -> None:
    _write(tmp_path / "src/a.py", "VALUE = 1\n")
    _write(tmp_path / "src/b.py", "VALUE = 2\n")
    _write(tmp_path / "node_modules/pkg/index.js", "function ignored() {}\n")
    _write(tmp_path / ".git/hooks/sample.py", "def ignored(): pass\n")

    index = CodebaseIndexer(tmp_path, max_files=1).build()

    assert index["summary"]["candidate_files"] == 2
    assert index["summary"]["indexed_files"] == 1
    assert index["summary"]["skipped_files"] == 1
    assert index["summary"]["truncated"] is True
    assert all("node_modules" not in item["path"] for item in index["files"])
    assert all(".git" not in item["path"] for item in index["files"])


def test_cache_loads_only_when_source_inventory_is_fresh(tmp_path) -> None:
    source = tmp_path / "module.py"
    _write(source, "def first():\n    return 1\n")
    indexer = CodebaseIndexer(tmp_path)
    index = indexer.build()
    indexer.write_json(index, tmp_path / "repo_dictionary.json")

    cached = CodebaseIndexer(tmp_path).load_cached()
    assert cached is not None
    assert cached["files"][0]["path"] == "module.py"

    _write(source, "def second():\n    return 2\n")
    os.utime(source, None)
    assert CodebaseIndexer(tmp_path).load_cached() is None


def test_cli_index_writes_json_to_requested_output(tmp_path) -> None:
    repository = tmp_path / "sample"
    _write(repository / "src/app.py", "class Application:\n    pass\n")
    output = tmp_path / "reports" / "dictionary.json"

    result = CliRunner().invoke(
        app,
        ["index", str(repository), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["files"][0]["path"] == "src/app.py"
    assert "1 files" in result.output
    assert "1 symbols" in result.output


def test_cli_index_defaults_to_repository_root(tmp_path) -> None:
    _write(tmp_path / "main.go", "package main\nfunc main() {}\n")

    result = CliRunner().invoke(app, ["index", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "repo_dictionary.json").is_file()


def test_cli_index_refuses_to_replace_a_symlink(tmp_path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    external = tmp_path / "external.json"
    external.write_text("{}", encoding="utf-8")
    output = repository / "repo_dictionary.json"
    try:
        output.symlink_to(external)
    except (OSError, NotImplementedError):
        return

    result = CliRunner().invoke(app, ["index", str(repository)])

    assert result.exit_code != 0
    assert external.read_text(encoding="utf-8") == "{}"
