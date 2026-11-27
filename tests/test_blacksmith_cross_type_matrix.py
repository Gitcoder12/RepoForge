"""Cross-language and cross-project-type smoke coverage for Blacksmith/Megazords.

These tests intentionally verify static inspection and recommendation behavior only.
They do not execute repository code or claim that suggested integrations are compatible.
"""

from __future__ import annotations

from pathlib import Path

from repoforge.blacksmith import Blacksmith
from repoforge.megazord import MegazordEngine


def _write_project(
    path: Path,
    *,
    readme: str,
    files: dict[str, str],
) -> Path:
    path.mkdir(parents=True)
    (path / "README.md").write_text(readme, encoding="utf-8")
    for relative_path, content in files.items():
        target = path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return path


def test_blacksmith_detects_common_languages_across_project_types(tmp_path: Path):
    projects = [
        ("python", "src/main.py", "requirements.txt", "Python"),
        ("javascript", "src/index.js", "package.json", "JavaScript"),
        ("typescript", "src/index.tsx", "package.json", "TypeScript"),
        ("go", "cmd/app/main.go", "go.mod", "Go"),
        ("rust", "src/lib.rs", "Cargo.toml", "Rust"),
        ("java", "src/Main.java", "pom.xml", "Java"),
        ("kotlin", "src/Main.kt", "build.gradle", "Kotlin"),
        ("csharp", "src/Program.cs", None, "C#"),
        ("cpp", "src/main.cpp", None, "C++"),
        ("c", "src/main.c", None, "C"),
        ("ruby", "lib/app.rb", "Gemfile", "Ruby"),
        ("php", "public/index.php", "composer.json", "PHP"),
        ("swift", "Sources/App.swift", None, "Swift"),
        ("dart", "lib/main.dart", None, "Dart"),
        ("shell", "scripts/run.sh", None, "Shell"),
        ("powershell", "scripts/run.ps1", None, "PowerShell"),
        ("sql", "sql/query.sql", None, "SQL"),
    ]

    for project_name, source_path, manifest, expected_language in projects:
        project = tmp_path / project_name
        files = {source_path: "// source fixture\n"}
        if manifest:
            files[manifest] = "# minimal manifest fixture\n"

        report = Blacksmith(
            _write_project(
                project,
                readme=f"# {project_name}\nCross-language inspection fixture.",
                files=files,
            )
        ).inspect()

        assert report["languages"].get(expected_language) == 1, (
            project_name,
            report["languages"],
        )
        assert report["scan_incomplete"] is False


def test_blacksmith_detects_terraform_capability_but_not_terraform_language(tmp_path: Path):
    project = _write_project(
        tmp_path / "terraform-platform",
        readme="# Terraform infrastructure as code deployment",
        files={"main.tf": 'resource "example" "one" {}\n'},
    )

    report = Blacksmith(project).inspect()

    # Current limitation: Terraform is inferred from README text, but .tf is
    # not in Blacksmith's source-extension catalogue yet.
    assert "infrastructure" in report["capabilities"]
    assert "Terraform" not in report["languages"]


def test_megazords_suggests_cross_language_frontend_backend_pairing(tmp_path: Path):
    frontend = _write_project(
        tmp_path / "react-frontend",
        readme="# React frontend dashboard built with Vite",
        files={
            "src/App.tsx": "export function App() { return null; }\n",
            "package.json": '{"name":"frontend","scripts":{"test":"vitest"}}\n',
        },
    )
    backend = _write_project(
        tmp_path / "go-backend",
        readme="# Go backend REST API service",
        files={
            "cmd/server/main.go": "package main\nfunc main() {}\n",
            "go.mod": "module example.com/backend\n",
        },
    )

    before = {
        project.name: sorted(item.relative_to(project).as_posix() for item in project.rglob("*"))
        for project in (frontend, backend)
    }
    report = MegazordEngine().suggest([frontend, backend])

    assert report["mode"] == "recommend_only"
    assert report["repositories_analyzed"] == 2
    assert report["pairings_evaluated"] == 1
    pairing = report["suggestions"][0]
    assert pairing["fit_score"] > 0
    assert pairing["shared_languages"] == []
    assert any(set(item["capabilities"]) == {"backend", "frontend"} for item in pairing["complementarity"])
    assert any(
        item["pattern"] == "Product interface + service"
        for item in pairing["integration_blueprint"]
    )
    after = {
        project.name: sorted(item.relative_to(project).as_posix() for item in project.rglob("*"))
        for project in (frontend, backend)
    }
    assert before == after


def test_megazords_suggests_ai_evaluation_pair_across_python_and_rust(tmp_path: Path):
    model = _write_project(
        tmp_path / "python-model",
        readme="# Machine learning model and data pipeline",
        files={
            "src/model.py": "MODEL = None\n",
            "pyproject.toml": "[project]\nname='model'\n",
        },
    )
    evaluation = _write_project(
        tmp_path / "rust-evaluator",
        readme="# Benchmark evaluation harness and model quality metrics",
        files={
            "src/main.rs": "fn main() {}\n",
            "Cargo.toml": "[package]\nname='evaluator'\nversion='0.1.0'\n",
        },
    )

    report = MegazordEngine().suggest([model, evaluation])
    pairing = report["suggestions"][0]

    assert set(pairing["shared_languages"]) == set()
    assert any(set(item["capabilities"]) == {"ai_ml", "evaluation"} for item in pairing["complementarity"])
    assert any(item["pattern"] == "Model + evaluation harness" for item in pairing["integration_blueprint"])


def test_blacksmith_gitignore_repair_is_safe_but_not_language_specific(tmp_path: Path):
    rust_project = _write_project(
        tmp_path / "rust-cli",
        readme="# Rust command line tool",
        files={"src/main.rs": "fn main() {}\n", "Cargo.toml": "[package]\n"},
    )

    result = Blacksmith(rust_project).run(apply_fixes=True)

    ignore_file = rust_project / ".gitignore"
    assert ignore_file.is_file()
    assert result["applied"] == [{"path": ".gitignore", "status": "created"}]
    ignore_text = ignore_file.read_text(encoding="utf-8")

    # Current generic adapter covers Python/JavaScript conventions, not Rust's
    # target directory. This is a known cross-language repair gap, not a test failure.
    assert "target/" not in ignore_text
    assert ".venv/" in ignore_text
