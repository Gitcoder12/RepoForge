import json

import pytest

from repoforge.forge import ForgeWorkflow


def test_parse_actions_accepts_valid_json_and_fenced_json():
    payload = {
        "actions": [
            {
                "type": "create",
                "file": "tests/test_new.py",
                "content": "def test_ok():\n    assert True\n",
            }
        ]
    }
    encoded = json.dumps(payload)
    assert ForgeWorkflow.parse_actions(encoded) == payload["actions"]
    fenced = "```json\n" + encoded + "\n```"
    assert ForgeWorkflow.parse_actions(fenced) == payload["actions"]


@pytest.mark.parametrize(
    "action",
    [
        {"type": "delete", "file": "old.py", "content": ""},
        {"type": "create", "file": "../escape.py", "content": ""},
        {"type": "modify", "file": "/etc/passwd", "content": ""},
        {"type": "create", "file": "C:/Windows/file", "content": ""},
        {"type": "modify", "file": ".env", "content": "SECRET=value"},
        {"type": "modify", "file": ".env.production", "content": "SECRET=value"},
        {"type": "create", "file": ".git/config", "content": "unsafe"},
        {"type": "create", "file": ".github/workflows/ci.yml", "content": "unsafe"},
        {"type": "create", "file": "safe.py", "content": 42},
    ],
)
def test_parse_actions_rejects_unsafe_or_invalid_actions(action):
    with pytest.raises(ValueError):
        ForgeWorkflow.parse_actions(json.dumps({"actions": [action]}))


def test_parse_actions_rejects_duplicate_paths():
    actions = [
        {"type": "create", "file": "same.py", "content": "a"},
        {"type": "modify", "file": "same.py", "content": "b"},
    ]
    with pytest.raises(ValueError, match="duplicate"):
        ForgeWorkflow.parse_actions(json.dumps({"actions": actions}))


def test_parse_actions_rejects_non_list_actions():
    with pytest.raises(ValueError, match="actions array"):
        ForgeWorkflow.parse_actions('{"actions": "not-a-list"}')


def test_forge_defaults_to_read_only_inspection(tmp_path):
    report = ForgeWorkflow().run(tmp_path, "add tests")
    assert report["status"] == "plan_only"
    assert report["safety"]["default_read_only"] is True
    assert report["safety"]["batch_writes_are_transactional"] is False
    assert report["safety"]["automatic_rollback"] is False
    assert report["mutation"]["status"] == "not_requested"


def test_repository_context_is_bounded_and_skips_sensitive_files(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "module.py").write_text("VALUE = 42\nAPI_KEY = 'do-not-read'\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("API_KEY=do-not-read\n", encoding="utf-8")
    (tmp_path / "secrets.json").write_text('{"token":"do-not-read"}', encoding="utf-8")

    context = ForgeWorkflow._read_repository_context(tmp_path)

    assert [item["path"] for item in context] == ["src/module.py"]
    assert "VALUE = 42" in context[0]["content"]
    assert "[REDACTED]" in context[0]["content"]
    assert "do-not-read" not in json.dumps(context)


def test_forge_prefers_indexed_source_files_that_match_the_request(tmp_path):
    from repoforge.forge import ForgeWorkflow

    _write = tmp_path / "README.md"
    _write.write_text("# Overview\n", encoding="utf-8")
    router = tmp_path / "src" / "router.ts"
    router.parent.mkdir()
    router.write_text("export class Router {}\n", encoding="utf-8")

    context = ForgeWorkflow._read_repository_context(
        tmp_path, max_files=1, preferred_paths=["src/router.ts"]
    )

    assert context[0]["path"] == "src/router.ts"


def test_forge_ranks_dictionary_paths_using_symbol_names_and_route_alias():
    dictionary = {
        "files": [
            {
                "path": "src/server.ts",
                "symbols": [{"name": "startServer"}],
            },
            {
                "path": "src/router/index.ts",
                "symbols": [{"name": "Router"}],
            },
        ]
    }

    paths = ForgeWorkflow._rank_dictionary_paths("Add a route to Express", dictionary)

    assert paths == ["src/router/index.ts"]


def test_forge_prompt_places_repo_dictionary_before_source_context():
    dictionary = {
        "schema_version": 1,
        "languages": {"typescript": 1},
        "summary": {"indexed_files": 1, "symbols": 1},
        "files": [
            {
                "path": "src/router.ts",
                "language": "typescript",
                "symbols": [{"kind": "class", "name": "Router", "line": 4, "end_line": 20}],
                "imports": [],
            }
        ],
        "dependencies": {"src/router.ts": []},
    }

    prompt = ForgeWorkflow._model_prompt(
        "Add a route",
        {"quality": 80},
        {"commands": []},
        [{"path": "src/router.ts", "content": "export class Router {}"}],
        dictionary,
    )

    assert prompt.index('"repo_dictionary"') < prompt.index('"source_context"')
    assert "Router" in prompt
    assert "untrusted structural evidence" in prompt


def test_forge_prompt_keeps_relevant_index_entries_ahead_of_large_repositories():
    files = [
        {
            "path": f"src/module_{number:03}.py",
            "language": "python",
            "symbols": [],
            "imports": [],
        }
        for number in range(150)
    ]
    files.append(
        {
            "path": "src/router/routes.py",
            "language": "python",
            "symbols": [{"kind": "class", "name": "Router", "line": 10, "end_line": 80}],
            "imports": [],
        }
    )
    dictionary = {
        "schema_version": 1,
        "languages": {"python": len(files)},
        "summary": {"indexed_files": len(files)},
        "files": files,
        "dependencies": {},
    }

    prompt = ForgeWorkflow._model_prompt(
        "Add a route",
        {},
        {},
        [],
        dictionary,
    )

    assert '"path": "src/router/routes.py"' in prompt
    assert '"name": "Router"' in prompt


def test_forge_prompt_includes_only_the_selected_project_memory():
    dictionary = {"schema_version": 1, "languages": {}, "summary": {}, "files": [], "dependencies": {}}
    prompt = ForgeWorkflow._model_prompt(
        "Review this API",
        {},
        {},
        [],
        dictionary,
        memory_context={
            "name": "api-audit",
            "notes": [
                {"created_at": "2026-11-22T00:00:00+00:00", "text": "Keep v1 response fields stable."}
            ],
        },
    )

    assert '"context": "api-audit"' in prompt
    assert "Keep v1 response fields stable." in prompt
    assert "historical context" in prompt


def test_forge_uses_active_memory_context_for_that_repository_only(tmp_path, monkeypatch):
    from repoforge.memory import MemoryContextStore

    repository = tmp_path / "service"
    repository.mkdir()
    other_repository = tmp_path / "other-service"
    other_repository.mkdir()
    monkeypatch.setenv("REPOFORGE_HOME", str(tmp_path / "repoforge-home"))
    store = MemoryContextStore()
    store.create(repository, "service-context")
    store.add_note(repository, "Do not break the existing REST routes.")
    store.create(other_repository, "other-context")

    report = ForgeWorkflow().run(repository, "Review the service")

    assert report["status"] == "plan_only"
    assert report["memory_context"] == {"name": "service-context", "notes_loaded": 1}


def test_forge_can_explicitly_select_an_inactive_memory_context(tmp_path, monkeypatch):
    from repoforge.memory import MemoryContextStore

    repository = tmp_path / "service"
    repository.mkdir()
    monkeypatch.setenv("REPOFORGE_HOME", str(tmp_path / "repoforge-home"))
    store = MemoryContextStore()
    store.create(repository, "active-context")
    store.create(repository, "alternate-context", switch=False)
    store.add_note(repository, "Alternate-context-only note.", name="alternate-context")

    report = ForgeWorkflow().run(
        repository,
        "Review the service",
        memory_context_name="alternate-context",
    )

    assert report["memory_context"] == {"name": "alternate-context", "notes_loaded": 1}
    assert store.load(repository)["name"] == "active-context"
