"""Read-only repository risk-signal scanner.

The scanner reports review leads, not proof of malicious intent or vulnerability.
It never imports or executes repository code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    severity: str
    pattern: re.Pattern[str]
    explanation: str
    recommendation: str


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: str
    path: str
    line: int
    evidence: str
    explanation: str
    recommendation: str


@dataclass(frozen=True)
class ScanReport:
    root: str
    files_scanned: int
    files_skipped: int
    bytes_scanned: int
    truncated: bool
    findings: tuple[Finding, ...]

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "bytes_scanned": self.bytes_scanned,
            "truncated": self.truncated,
            "finding_count": len(self.findings),
            "findings": [asdict(item) for item in self.findings],
            "disclaimer": (
                "Heuristic review signals only; findings require human verification. "
                "No repository code was executed."
            ),
        }


RULES = (
    Rule(
        "RF-SEN-001",\n        "Dynamic code execution",\n        "high",
        re.compile(r"\b(eval|exec)\s*\("),
        "Dynamic evaluation can execute data as code depending on its inputs.",
        "Trace input provenance; prefer constrained parsers or explicit dispatch.",
    ),
    Rule(
        "RF-SEN-002", "Shell-enabled subprocess", "high",
        re.compile(r"\bsubprocess\.(run|Popen|call|check_call|check_output)\s*\([^\n]*\bshell\s*=\s*True"),
        "Shell interpretation increases command-injection exposure when inputs are untrusted.",
        "Prefer argument arrays with shell=False and validate every argument.",
    ),
    Rule(
        "RF-SEN-003",\n        "Legacy command execution",\n        "high",
        re.compile(r"\bos\.system\s*\("),
        "os.system delegates command execution to a shell.",
        "Use subprocess with an argument array and explicit environment/timeout controls.",
    ),
    Rule(
        "RF-SEN-004",\n        "Pickle deserialization",\n        "high",
        re.compile(r"\bpickle\.(load|loads)\s*\("),
        "Untrusted pickle payloads can execute code during deserialization.",
        "Never load untrusted pickle data; use a non-executable data format.",
    ),
    Rule(
        "RF-SEN-005",\n        "Potentially unsafe YAML loader",\n        "medium",
        re.compile(r"\byaml\.load\s*\("),
        "yaml.load may construct arbitrary Python objects unless a safe loader is explicitly used.",
        "Use yaml.safe_load or explicitly pass SafeLoader; verify the call context.",
    ),
)


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build",
}
TEXT_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".java", ".kt", ".go", ".rs", ".rb", ".php", ".sh", ".bash",
    ".yaml", ".yml", ".toml", ".ini", ".cfg",
}
MAX_FILE_BYTES = 1_000_000


def _iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            name\n            for name in dirs
            if name not in SKIP_DIRS and not (Path(current) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(current) / name
            if path.suffix.lower() in TEXT_SUFFIXES and not path.is_symlink():
                yield path


def scan_repository(
    root: str | Path, *, max_files: int = 10000, max_total_bytes: int = 50_000_000
) -> ScanReport:
    target = Path(root).expanduser().resolve()
    if not target.is_dir():
        raise ValueError("repository path must be an existing directory")
    if max_files < 1 or max_total_bytes < 1:
        raise ValueError("max_files and max_total_bytes must be positive")

    findings: list[Finding] = []
    scanned = skipped = bytes_scanned = 0
    truncated = False

    for index, path in enumerate(_iter_files(target)):
        if index >= max_files:
            truncated = True
            break
        try:
            file_size = path.stat().st_size
            if file_size > MAX_FILE_BYTES:
                skipped += 1
                continue
            if bytes_scanned + file_size > max_total_bytes:
                truncated = True
                break
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            skipped += 1
            continue

        scanned += 1
        bytes_scanned += file_size
        relative = path.relative_to(target).as_posix()
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule in RULES:
                if rule.pattern.search(line):
                    findings.append(Finding(
                        rule.rule_id, rule.title, rule.severity, relative, line_number,
                        line.strip()[:240], rule.explanation, rule.recommendation,
                    ))

    return ScanReport(
        str(target), scanned, skipped, bytes_scanned, truncated, tuple(findings)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only RepoForge risk-signal scan")
    parser.add_argument("repository", nargs="?", default=".")
    parser.add_argument("--max-files", type=int, default=10000)
    parser.add_argument("--max-total-bytes", type=int, default=50_000_000)
    args = parser.parse_args()
    try:
        report = scan_repository(
            args.repository,
            max_files=args.max_files,
            max_total_bytes=args.max_total_bytes,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
