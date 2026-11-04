import os
import fnmatch
import logging
import re
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger("RepoForge.Scanner")

@dataclass
class LanguageStats:
    files: int = 0
    lines: int = 0
    bytes: int = 0

@dataclass
class RepoMetadata:
    has_readme: bool = False
    has_license: bool = False
    has_dockerfile: bool = False
    has_github_actions: bool = False
    has_tests_dir: bool = False
    has_docs_dir: bool = False
    has_ci_config: bool = False
    build_files: List[str] = field(default_factory=list)
    important_files: List[str] = field(default_factory=list)

@dataclass
class ScanResult:
    repo_path: str
    statistics: Dict[str, int]
    languages: Dict[str, LanguageStats]
    metadata: RepoMetadata
    profile: Dict[str, str]
    important_files: List[str]
    threats: List[Dict[str, any]] = field(default_factory=list) # NIGHT VISION

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "statistics": self.statistics,
            "languages": {k: asdict(v) for k, v in self.languages.items()},
            "metadata": asdict(self.metadata),
            "profile": self.profile,
            "important_files": self.important_files,
            "threats": self.threats,
        }

class RepoScanner:
    IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "env", "dist", "build", ".idea", ".vscode", "coverage", ".pytest_cache", ".mypy_cache", ".tox", "eggs", "*.egg-info"}
    IGNORE_FILES = {"*.pyc", "*.pyo", "*.so", "*.dylib", "*.dll", "*.exe", "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.mp4", "*.mp3", "*.wav", "*.pdf", "*.zip", "*.tar.gz", "*.tgz"}
    
    EXT_MAP = {
        ".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".jsx": "React", ".tsx": "React",
        ".html": "HTML", ".css": "CSS", ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++", ".h": "C/C++ Header",
        ".java": "Java", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".sh": "Shell", ".bash": "Shell",
        ".md": "Markdown", ".rst": "reStructuredText", ".txt": "Text", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML"
    }
    
    BUILD_FILES = {"pyproject.toml", "setup.py", "requirements.txt", "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "CMakeLists.txt", "Makefile"}

    SECURITY_RULES = {
        "dangerous_functions": [
            (r"\beval\(", "CRITICAL", "Use of eval() can lead to arbitrary code execution."),
            (r"\bexec\(", "CRITICAL", "Use of exec() can lead to arbitrary code execution."),
            (r"os\.system\(", "HIGH", "Use of os.system() is vulnerable to command injection."),
            (r"subprocess\.call\(.*shell\s*=\s*True", "CRITICAL", "Shell=True in subprocess is a command injection risk."),
            (r"pickle\.loads?\(", "HIGH", "Unpickling untrusted data can execute arbitrary code.")
        ],
        "secrets": [
            (r"(?i)aws_access_key_id\s*=\s*['\"][A-Z0-9]{20}['\"]", "CRITICAL", "Hardcoded AWS Access Key detected."),
            (r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]", "CRITICAL", "Hardcoded AWS Secret Key detected."),
            (r"(?i)api_key\s*=\s*['\"][a-zA-Z0-9]{32}['\"]", "CRITICAL", "Hardcoded API Key detected."),
            (r"-----BEGIN RSA PRIVATE KEY-----", "CRITICAL", "Hardcoded RSA Private Key detected.")
        ]
    }

    def __init__(self, repo_path: str, max_file_size_mb: int = 5):
        self.repo_path = Path(repo_path).resolve()
        self.max_bytes = max_file_size_mb * 1024 * 1024
        self._reset()

    def _reset(self):
        self.stats = defaultdict(int)
        self.lang_stats = defaultdict(LanguageStats)
        self.metadata = RepoMetadata()
        self.important_files = []
        self.threats = []
        self.primary_language = "Unknown"
        self.repo_type = "unknown"

    def scan(self) -> ScanResult:
        self._reset()
        if not self.repo_path.exists():
            logger.error(f"Path not found: {self.repo_path}")
            raise FileNotFoundError(f"Path not found: {self.repo_path}")

        logger.info(f"🔍 Scanning repository (Night Vision Active): {self.repo_path}")

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in self.IGNORE_DIRS)]
            rel_root = Path(root).relative_to(self.repo_path)
            self._detect_dir_signals(rel_root)

            for f in files:
                if any(fnmatch.fnmatch(f, p) for p in self.IGNORE_FILES):
                    continue
                fp = Path(root) / f
                rp = rel_root / f
                try:
                    self._process_file(fp, rp)
                except (OSError, PermissionError, UnicodeDecodeError) as e:
                    logger.warning(f"⚠️ Skipped {rp}: {e}")
                    continue

        self._finalize()
        logger.info(f"✅ Scan complete: {self.stats['total_files']} files, {self.stats['total_lines']} lines. Threats found: {len(self.threats)}")
        
        return ScanResult(
            repo_path=str(self.repo_path),
            statistics=dict(self.stats),
            languages=dict(self.lang_stats),
            metadata=self.metadata,
            profile={"primary_language": self.primary_language, "repo_type": self.repo_type},
            important_files=sorted(self.important_files),
            threats=self.threats
        )

    def _night_vision_scan(self, source_code: str, rel_path: str):
        for category, rules in self.SECURITY_RULES.items():
            for pattern, severity, description in rules:
                for match in re.finditer(pattern, source_code):
                    line_num = source_code[:match.start()].count('\n') + 1
                    self.threats.append({
                        "file": str(rel_path),
                        "line": line_num,
                        "severity": severity,
                        "category": category,
                        "description": description,
                        "snippet": match.group(0)[:50] + "..."
                    })

    def _detect_dir_signals(self, rel: Path):
        parts = str(rel).split(os.sep)
        if parts[0] in ("tests", "test"): self.metadata.has_tests_dir = True
        if parts[0] in ("docs", "documentation"): self.metadata.has_docs_dir = True
        if parts[0] == ".github" and "workflows" in parts: self.metadata.has_github_actions = True

    def _process_file(self, full: Path, rel: Path):
        ext = full.suffix.lower()
        if full.name == "Dockerfile": ext = ".dockerfile"
        if full.name in self.BUILD_FILES:
            self.metadata.build_files.append(str(rel))
            self.important_files.append(str(rel))

        name_low = full.name.lower()
        if name_low.startswith("readme"): self.metadata.has_readme = True; self.important_files.append(str(rel))
        if name_low in ("license", "license.md", "copying"): self.metadata.has_license = True; self.important_files.append(str(rel))
        if name_low == "dockerfile": self.metadata.has_dockerfile = True; self.important_files.append(str(rel))

        lang = self.EXT_MAP.get(ext, "Unknown")
        size = full.stat().st_size
        self.stats["total_bytes"] += size
        self.stats["total_files"] += 1

        lines = 0
        is_binary = False
        if size < self.max_bytes:
            try:
                source_code = full.read_text(encoding='utf-8', errors='ignore')
                lines = source_code.count('\n') + 1
                self.stats["total_lines"] += lines
                
                # NIGHT VISION SCAN
                if ext in [".py", ".js", ".ts", ".env", ".json", ".yaml", ".yml"]:
                    self._night_vision_scan(source_code, rel)
                    
            except (UnicodeDecodeError, PermissionError):
                is_binary = True

        if lang != "Unknown":
            self.lang_stats[lang].files += 1
            self.lang_stats[lang].bytes += size
            if not is_binary: self.lang_stats[lang].lines += lines

    def _finalize(self):
        if self.lang_stats:
            primary = max(self.lang_stats.items(), key=lambda x: x[1].bytes)
            self.primary_language = primary[0]
        if "pyproject.toml" in self.metadata.build_files or "setup.py" in self.metadata.build_files:
            self.repo_type = "Python Package"
        elif "package.json" in self.metadata.build_files:
            self.repo_type = "Node.js Project"
        elif "Cargo.toml" in self.metadata.build_files:
            self.repo_type = "Rust Project"
        elif "go.mod" in self.metadata.build_files:
            self.repo_type = "Go Project"
        else:
            self.repo_type = "Application"

def scan_repository(repo_path: str, max_file_size_mb: int = 5) -> dict:
    scanner = RepoScanner(repo_path, max_file_size_mb)
    return scanner.scan().to_dict()
