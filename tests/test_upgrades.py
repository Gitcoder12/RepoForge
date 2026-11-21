from __future__ import annotations

from repoforge.upgrades import UpgradePlanner


def snapshot_with_all_gaps():
    return {
        "name": "demo",
        "scan_incomplete": False,
        "signals": {
            "readme": False, "tests": False, "ci": False, "license": False,
            "gitignore": False, "security_process": False, "quality_tooling": False,
        },
        "rank": {
            "score": 0, "grade": "E", "maximum": 100,
            "dimensions": {"project_configuration": 0},
        },
    }


def test_upgrade_catalogue_lists_ranked_options_for_detected_gaps():
    report = UpgradePlanner().build(snapshot_with_all_gaps())
    ids = {item["id"] for item in report["options"]}
    assert {
        "docs-readme", "tests-real", "ci-pipeline", "project-manifest",
        "license-choice", "gitignore", "security-baseline", "quality-tooling",
    } <= ids
    assert report["summary"]["options_available"] == 8
    assert report["options"] == sorted(
        report["options"], key=lambda item: (-item["priority_score"], -item["rank_points_available"], item["id"])  # noqa: E501
    )


def test_upgrade_profiles_filter_options():
    planner = UpgradePlanner()
    report = planner.build(snapshot_with_all_gaps())
    security = planner.select(report, profile="security")
    assert [item["id"] for item in security["selected_options"]] == ["security-baseline"]


def test_explicit_selection_overrides_profile():
    planner = UpgradePlanner()
    report = planner.build(snapshot_with_all_gaps())
    selected = planner.select(report, profile="security", option_ids=["tests-real", "gitignore"])
    assert {item["id"] for item in selected["selected_options"]} == {"tests-real", "gitignore"}
    assert selected["selection_mode"] == "explicit_ids"


def test_unknown_upgrade_option_is_rejected():
    planner = UpgradePlanner()
    report = planner.build(snapshot_with_all_gaps())
    try:
        planner.select(report, option_ids=["not-real"])
    except ValueError as exc:
        assert "unknown upgrade option" in str(exc)
    else:
        raise AssertionError("unknown option should be rejected")


def test_invalid_profile_is_rejected():
    planner = UpgradePlanner()
    report = planner.build(snapshot_with_all_gaps())
    try:
        planner.select(report, profile="magic")
    except ValueError as exc:
        assert "profile must be one of" in str(exc)
    else:
        raise AssertionError("invalid profile should be rejected")


def test_complete_repository_has_no_missing_signal_upgrades():
    snapshot = snapshot_with_all_gaps()
    snapshot["signals"] = {key: True for key in snapshot["signals"]}
    snapshot["rank"]["dimensions"]["project_configuration"] = 15
    report = UpgradePlanner().build(snapshot)
    assert report["options"] == []
    assert report["summary"]["rank_points_available"] == 0


def test_license_choice_is_never_automatic():
    report = UpgradePlanner().build(snapshot_with_all_gaps())
    option = next(item for item in report["options"] if item["id"] == "license-choice")
    assert option["automation"] == "human_approved"
    assert "never select one automatically" in option["implementation"]


def test_upgrade_plan_is_recommend_only_and_does_not_execute_code():
    report = UpgradePlanner().build(snapshot_with_all_gaps())
    assert report["safety"]["default"] == "recommend_only"
    assert report["safety"]["no_target_code_execution"] is True
    assert report["safety"]["no_overwrite_or_delete"] is True


def test_blacksmith_report_includes_upgrade_catalogue(tmp_path):
    from repoforge.blacksmith import Blacksmith

    report = Blacksmith(tmp_path).run()
    assert report["upgrade_options"]["engine"] == "UpgradeForge"
    assert report["upgrade_options"]["summary"]["options_available"] > 0


def test_upgrade_cli_emits_profile_filtered_json(tmp_path):
    import json

    from typer.testing import CliRunner

    from repoforge.cli import app

    result = CliRunner().invoke(app, ["upgrade", str(tmp_path), "--profile", "security"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["selected_profile"] == "security"
    assert all(item["profile"] == "security" for item in payload["selected_options"])
