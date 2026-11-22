"""Coverage for RepoDictionary built-in and third-party language adapters."""

from pathlib import Path

from repoforge.dictionary import CodebaseIndexer, LanguageAdapter, register_language_adapter


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_indexes_additional_languages_and_resolves_local_dependencies(tmp_path) -> None:
    _write(
        tmp_path / "src/Main.java",
        "package demo;\nimport java.util.List;\npublic class Main {\n"
        "    public static void start() {}\n}\n",
    )
    _write(tmp_path / "src/main.rs", "use crate::helper;\npub fn main_entry() {}\n")
    _write(tmp_path / "src/helper.rs", "pub fn helper() {}\n")
    _write(
        tmp_path / "lib/app.rb",
        "class App\n  def run\n  end\nend\nrequire_relative './helpers'\n",
    )
    _write(tmp_path / "lib/helpers.rb", "module Helpers\nend\n")
    _write(tmp_path / "native/app.c", '#include "config.h"\nint main(void) { return 0; }\n')
    _write(tmp_path / "native/config.h", "#define APP_PORT 8080\n")
    _write(
        tmp_path / "infra/main.tf",
        'module "network" {\n  source = "./modules/network"\n}\nvariable "region" {}\n',
    )
    _write(tmp_path / "infra/modules/network/main.tf", 'output "id" {}\n')
    _write(tmp_path / "api/schema.graphql", "type Query {\n  status: String\n}\n")
    _write(tmp_path / "api/service.proto", 'message Request {}\nservice Api {}\n')

    index = CodebaseIndexer(tmp_path).build()
    files = {item["path"]: item for item in index["files"]}

    assert {"java", "rust", "ruby", "c", "terraform", "graphql", "proto"} <= set(
        index["languages"]
    )
    assert ("type", "Main") in {
        (item["kind"], item["name"]) for item in files["src/Main.java"]["symbols"]
    }
    assert ("function", "main_entry") in {
        (item["kind"], item["name"]) for item in files["src/main.rs"]["symbols"]
    }
    assert ("type", "Query") in {
        (item["kind"], item["name"]) for item in files["api/schema.graphql"]["symbols"]
    }
    assert ("service", "Api") in {
        (item["kind"], item["name"]) for item in files["api/service.proto"]["symbols"]
    }
    assert index["dependencies"]["src/main.rs"] == ["src/helper.rs"]
    assert index["dependencies"]["lib/app.rb"] == ["lib/helpers.rb"]
    assert index["dependencies"]["native/app.c"] == ["native/config.h"]
    assert index["dependencies"]["infra/main.tf"] == ["infra/modules/network/main.tf"]


def test_custom_language_adapter_can_be_registered(tmp_path) -> None:
    register_language_adapter(
        LanguageAdapter(
            language="zig",
            extensions=(".zig",),
            symbol_patterns=(("function", r"^\s*pub\s+fn\s+(?P<name>[A-Za-z_]\w*)"),),
            import_patterns=(r'@import\s*\(\s*"(?P<module>[^"]+)"\s*\)',),
        )
    )
    _write(
        tmp_path / "src/main.zig",
        'const std = @import("std");\npub fn main() void {}\n',
    )

    index = CodebaseIndexer(tmp_path).build()

    assert index["languages"] == {"zig": 1}
    symbols = {(item["kind"], item["name"]) for item in index["files"][0]["symbols"]}
    assert ("function", "main") in symbols
    assert ("import", "std") in symbols
