"""Validate machine-readable platform blueprint configuration files."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_config(name: str):
    path = ROOT / "configs" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_platform_configs_are_valid_json():
    paths = sorted((ROOT / "configs").glob("*.json"))

    assert paths
    for path in paths:
        json.loads(path.read_text(encoding="utf-8"))


def test_failover_config_defaults_to_no_quota_switch_and_no_mock():
    config = _load_config("model_failover.json")

    assert config["primary"]["provider"] == "deepseek"
    assert config["policy"]["fallback_on_rate_limit"] is False
    assert config["policy"]["never_fallback_to_implicit_mock"] is True
    assert config["policy"]["fallback_on_authentication_error"] is False


def test_ark_power_policy_is_simulation_only_and_revokes_on_unknowns():
    config = _load_config("ark_powerup_policy.json")

    assert config["execution_scope"] == "simulation_only"
    assert "monitor_disagreement" in config["revocation_triggers"]
    assert "telemetry_stale" in config["revocation_triggers"]
    assert "zero_probability_of_rogue_behavior" in config["prohibited_guarantees"]


def test_safebreak_incident_keeps_vendor_attribution_and_unknown_counts():
    config = _load_config("safebreak_incidents.json")
    incident = config["records"][0]

    assert incident["event_start"] == "2026-11-12"
    assert incident["event_end"] == "2026-11-14"
    assert incident["impact"]["numeric_customer_impact"] is None
    assert incident["final_vendor_postmortem_available"] is False
    assert incident["sources"]


def test_cloud_locations_do_not_claim_undisclosed_facility_coordinates():
    config = _load_config("datacenter_regions.json")

    assert config["precision_policy"]["latitude_longitude"] is None
    assert config["precision_policy"]["building_level_addresses"] == "not_publicly_asserted"
    assert any(
        item["provider"] == "AWS" and item["region_code"] == "ap-south-2"
        for item in config["locations"]
    )
    assert any(
        item["provider"] == "Google Cloud" and item["region_code"] == "asia-south2"
        for item in config["locations"]
    )


def test_company_catalogue_does_not_claim_a_safety_or_quality_ranking():
    config = _load_config("ai_robotics_landscape.json")

    companies = {entry["company"] for entry in config["entries"]}
    assert {"OpenAI", "Anthropic", "Google DeepMind", "NVIDIA", "Neuralink"} <= companies
    assert any(
        "does not imply independent verification" in rule
        for rule in config["evidence_rules"]
    )
