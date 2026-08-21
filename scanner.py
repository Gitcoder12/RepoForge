import os
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json
import time

# ================================================================
# Data structures – engine‑ready
# ================================================================

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
    statistics: Dict[str, int]          # total_files, total_lines, total_bytes
    languages: Dict[str, LanguageStats]
    metadata: RepoMetadata
    profile: Dict[str, str]             # primary_language, repo_type
    important_files: List[str]

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "statistics": self.statistics,
            "languages": {k: asdict(v) for k, v in self.languages.items()},
            "metadata": asdict(self.metadata),
            "profile": self.profile,
            "important_files": self.important_files,
        }

# ================================================================
# Scanner – one pass, crash‑proof, extensible
# ================================================================

class RepoScanner:
    IGNORE_DIRS = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "env", "dist", "build", ".idea", ".vscode", "coverage",
        ".pytest_cache", ".mypy_cache", ".tox", "eggs", "*.egg-info"
    }
    IGNORE_FILES = {
        "*.pyc", "*.pyo", "*.so", "*.dylib", "*.dll", "*.exe",
        "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.mp4",
        "*.mp3", "*.wav", "*.pdf", "*.zip", "*.tar.gz", "*.tgz"
    }
    EXT_MAP = {
        ".py": "Python", ".pyi": "Python",
        ".js": "JavaScript", ".ts": "TypeScript", ".jsx": "React", ".tsx": "React",
        ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "SASS",
        ".vue": "Vue", ".svelte": "Svelte",
        ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++", ".h": "C/C++ Header",
        ".hpp": "C++ Header", ".cs": "C#", ".rb": "Ruby", ".swift": "Swift",
        ".kt": "Kotlin", ".kts": "Kotlin Script",
        ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
        ".xml": "XML", ".sql": "SQL",
        ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
        ".ps1": "PowerShell",
        ".java": "Java", ".scala": "Scala", ".clj": "Clojure",
        ".lua": "Lua", ".r": "R", ".dart": "Dart",
        ".dockerfile": "Dockerfile",
        ".md": "Markdown", ".rst": "reStructuredText", ".txt": "Text",
    }
    BUILD_FILES = {
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
        "package.json", "package-lock.json", "yarn.lock",
        "Cargo.toml", "Cargo.lock",
        "go.mod", "go.sum",
        "pom.xml", "build.gradle", "build.gradle.kts",
        "CMakeLists.txt", "Makefile", "configure",
        "composer.json", "Gemfile", "Podfile",
        "mix.exs", "rebar.config"
    }

    def __init__(self, repo_path: str, max_file_size_mb: int = 5):
        self.repo_path = Path(repo_path).resolve()
        self.max_bytes = max_file_size_mb * 1024 * 1024
        self.stats = defaultdict(int)
        self.lang_stats = defaultdict(LanguageStats)
        self.metadata = RepoMetadata()
        self.important_files = []
        self.primary_language = "Unknown"
        self.repo_type = "unknown"

    def scan(self) -> ScanResult:
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Path not found: {self.repo_path}")

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not self._ignore_dir(root, d)]
            rel_root = Path(root).relative_to(self.repo_path)

            self._detect_dir_signals(rel_root)

            for f in files:
                if self._ignore_file(f):
                    continue
                fp = Path(root) / f
                rp = rel_root / f
                try:
                    self._process_file(fp, rp)
                except (OSError, PermissionError, UnicodeDecodeError):
                    continue

        self._finalize()
        return ScanResult(
            repo_path=str(self.repo_path),
            statistics=dict(self.stats),
            languages=dict(self.lang_stats),
            metadata=self.metadata,
            profile={"primary_language": self.primary_language, "repo_type": self.repo_type},
            important_files=sorted(self.important_files),
        )

    def _ignore_dir(self, root: str, d: str) -> bool:
        return any(fnmatch.fnmatch(d, p) for p in self.IGNORE_DIRS)

    def _ignore_file(self, f: str) -> bool:
        return any(fnmatch.fnmatch(f, p) for p in self.IGNORE_FILES)

    def _detect_dir_signals(self, rel: Path):
        parts = str(rel).split(os.sep)
        if parts[0] in ("tests", "test"):
            self.metadata.has_tests_dir = True
        if parts[0] in ("docs", "documentation"):
            self.metadata.has_docs_dir = True
        if parts[0] == ".github" and "workflows" in parts:
            self.metadata.has_github_actions = True

    def _process_file(self, full: Path, rel: Path):
        ext = full.suffix.lower()
        if full.name == "Dockerfile":
            ext = ".dockerfile"

        # Build files
        if full.name in self.BUILD_FILES:
            self.metadata.build_files.append(str(rel))
            self.important_files.append(str(rel))

        # Special files
        name_low = full.name.lower()
        if name_low in ("readme.md", "readme.rst", "readme.txt", "readme"):
            self.metadata.has_readme = True
            self.important_files.append(str(rel))
        if name_low in ("license", "license.md", "license.txt", "copying"):
            self.metadata.has_license = True
            self.important_files.append(str(rel))
        if name_low in (".travis.yml", ".gitlab-ci.yml", "jenkinsfile", "circle.yml"):
            self.metadata.has_ci_config = True
            self.important_files.append(str(rel))
        if name_low == "dockerfile":
            self.metadata.has_dockerfile = True
            self.important_files.append(str(rel))

        # Language & stats
        lang = self.EXT_MAP.get(ext, "Unknown")
        size = full.stat().st_size
        self.stats["total_bytes"] += size

        lines = 0
        is_binary = False
        if size < self.max_bytes:
            try:
                with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                    lines = sum(1 for _ in fh)
            except (UnicodeDecodeError, PermissionError):
                is_binary = True
                lines = 0
        else:
            is_binary = True

        self.stats["total_files"] += 1
        if not is_binary:
            self.stats["total_lines"] += lines

        if lang != "Unknown":
            self.lang_stats[lang].files += 1
            self.lang_stats[lang].bytes += size
            if not is_binary:
                self.lang_stats[lang].lines += lines

    def _finalize(self):
        if self.lang_stats:
            primary = max(self.lang_stats.items(), key=lambda x: x[1].bytes)
            self.primary_language = primary[0]

        if "pyproject.toml" in self.metadata.build_files or "setup.py" in self.metadata.build_files:
            self.repo_type = "Python Package" if self.primary_language == "Python" else "Application"
        elif "package.json" in self.metadata.build_files:
            self.repo_type = "Node.js Project"
        elif "Cargo.toml" in self.metadata.build_files:
            self.repo_type = "Rust Project"
        elif "go.mod" in self.metadata.build_files:
            self.repo_type = "Go Project"
        else:
            self.repo_type = "Unknown"

        if any("cli" in f.lower() for f in self.important_files) and self.repo_type == "Unknown":
            self.repo_type = "CLI Tool"

# ================================================================
# Public entry point – drop‑in replacement
# ================================================================

def scan_repository(repo_path: str, max_file_size_mb: int = 5) -> dict:
    """Returns dict with keys: statistics, languages, metadata, profile, important_files.
    Fully backward compatible – adds new fields, never removes old ones."""
    scanner = RepoScanner(repo_path, max_file_size_mb)
    result = scanner.scan()
    return result.to_dict()

# ================================================================
# Self‑test – run with `python scanner.py /some/repo`
# ================================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scanner.py /path/to/repo")
        sys.exit(1)
    start = time.time()
    data = scan_repository(sys.argv[1])
    print(json.dumps(data, indent=2, default=str))
    print(f"\n✅ Scanned in {time.time()-start:.2f}s")
    print(f"Files: {data['statistics']['total_files']}")
    print(f"Primary lang: {data['profile']['primary_language']}")
    print(f"Repo type: {data['profile']['repo_type']}")
    print(f"Tests: {data['metadata']['has_tests_dir']}")