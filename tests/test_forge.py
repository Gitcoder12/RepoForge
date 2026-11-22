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


def test_parse_actions_rejects_non_object_envelope():
    with pytest.raises(ValueError, match="JSON object"):
        ForgeWorkflow.parse_actions('{"actions": "not-a-list"}')


def test_forge_defaults_to_read_only_inspection(tmp_path):
    report = ForgeWorkflow().run(tmp_path, "add tests")
    assert report["status"] == "plan_only"
    assert report["safety"]["default_read_only"] is True
    assert report["mutation"]["status"] == "not_requested"
