"""Exercise Blacksmith and Megazords against real checkouts plus a disposable fixture."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from repoforge.blacksmith import Blacksmith
from repoforge.megazord import MegazordEngine


def _snapshot(path: Path) -> dict[str, Any]:
    report = Blacksmith(path).inspect()
    if report["scan_incomplete"]:
        raise RuntimeError(f"Blacksmith scan incomplete for {path}: {report['scan_errors']}")
    return {
        "name": report["name"],
        "files_scanned": report["files_scanned"],
        "rank": report["rank"],
        "languages": report["languages"],
        "capabilities": report["capabilities"],
        "signals": report["signals"],
        "findings": report["findings"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ark-path", type=Path, required=True)
    parser.add_argument("--repoforge-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ark_path = args.ark_path.resolve()
    repoforge_path = args.repoforge_path.resolve()
    if not ark_path.is_dir() or not repoforge_path.is_dir():
        raise SystemExit("Both ARK and RepoForge paths must exist and be directories.")

    # Read-only inspections of the actual repositories.
    ark_snapshot = _snapshot(ark_path)
    repoforge_snapshot = _snapshot(repoforge_path)

    # Exercise the one supported write only inside a disposable temporary repo.
    with tempfile.TemporaryDirectory(prefix="repoforge-blacksmith-smoke-") as temp_dir:
        fixture = Path(temp_dir) / "sample-project"
        fixture.mkdir()
        (fixture / "README.md").write_text("# Disposable smoke project\n", encoding="utf-8")
        before = Blacksmith(fixture).inspect()
        applied = Blacksmith(fixture).run(apply_fixes=True)
        if applied["applied"] != [{"path": ".gitignore", "status": "created"}]:
            raise AssertionError(f"Unexpected Blacksmith repair result: {applied['applied']}")
        if applied["after"]["rank"]["score"] != before["rank"]["score"] + 5:
            raise AssertionError("Expected the .gitignore signal to increase RepoRank by 5.")
        if not (fixture / ".gitignore").is_file():
            raise AssertionError("Blacksmith did not create the expected .gitignore.")

    # Megazords compares the real local repositories without changing either.
    pairing_report = MegazordEngine().suggest([ark_path, repoforge_path], top_k=5)
    if pairing_report["repositories_analyzed"] != 2:
        raise AssertionError("Megazords did not analyze both repositories.")
    if pairing_report["pairings_evaluated"] != 1:
        raise AssertionError("Megazords should evaluate exactly one repository pair.")

    result = {
        "status": "passed",
        "blacksmith": {
            "actual_repositories_read_only": [ark_snapshot, repoforge_snapshot],
            "disposable_apply_demo": {
                "mode": applied["mode"],
                "applied": applied["applied"],
                "rank_before": before["rank"]["score"],
                "rank_after": applied["after"]["rank"]["score"],
                "rank_change": applied["rank_change"],
            },
        },
        "megazords": {
            "repositories_analyzed": pairing_report["repositories_analyzed"],
            "pairings_evaluated": pairing_report["pairings_evaluated"],
            "repositories": pairing_report["repositories"],
            "suggestions": pairing_report["suggestions"],
            "method": pairing_report["method"],
            "notices": pairing_report["notices"],
        },
        "safety": {
            "actual_repositories_modified": False,
            "test_or_build_commands_executed_in_targets": False,
            "automatic_integration_performed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
