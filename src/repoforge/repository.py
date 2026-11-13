"""Repository intake for local paths, GitHub URLs, and owner/repository names."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", "target", ".next", ".nuxt", ".tox",
}
_SECRET_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "credentials.json", "secrets.json",
}
_SKIP_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".keystore", ".jks",
    ".sqlite", ".db", ".zip", ".gz", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".pdf", ".lock",
}
_LANGUAGE_BY_SUFFIX = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go",
    ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".cs": "C#", ".cpp": "C++", ".c": "C", ".h": "C/C++",
    ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".json": "JSON", ".md": "Markdown",
}


@dataclass(frozen=True)
class RepositoryTarget:
    """Resolved repository location and its source."""

    reference: str
    path: Path
    cloned: bool
    remote_url: str | None = None


def _github_remote(reference: str) -> tuple[str, str] | None:
    value = reference.strip()
    if not value:
        return None

    ssh_match = re.fullmatch(
        r"git@github\.com:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?",
        value,
    )
    if ssh_match:
        owner, repo = ssh_match.groups()
    else:
        candidate = value if "://" in value else ""
        if not candidate and re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value
        ):
            owner, repo = value.split("/", 1)
        elif candidate:
            parsed = urlparse(candidate)
            if parsed.scheme != "https" or parsed.hostname != "github.com":
                raise ValueError("Only HTTPS GitHub URLs are supported; use a local path otherwise")
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 2:
                raise ValueError("GitHub URL must include an owner and repository name")
            owner, repo = parts[0], parts[1]
            if repo.endswith(".git"):
                repo = repo[:-4]
        else:
            return None

    if owner in {".", ".."} or repo in {".", ".."}:
        raise ValueError("Invalid GitHub repository reference")
    return owner, repo


def resolve_repository(
    reference: str,
    *,
    cache_dir: str | Path | None = None,
    clone_timeout: int = 300,
) -> RepositoryTarget:
    """Resolve a local repository or clone a GitHub repository into a local cache.

    Existing local directories take precedence over owner/repository parsing.
    Existing cached clones are reused only when their origin matches the request.
    """
    local_path = Path(reference).expanduser()
    if local_path.exists():
        if not local_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {local_path}")
        resolved = local_path.resolve(strict=True)
        if not (resolved / ".git").exists():
            raise ValueError(f"Directory is not a Git repository: {resolved}")
        return RepositoryTarget(reference, resolved, False, None)

    parsed = _github_remote(reference)
    if parsed is None:
        raise ValueError(
            "Repository must be an existing local Git directory, a GitHub URL, or owner/repo"
        )
    owner, repo = parsed
    remote = f"https://github.com/{owner}/{repo}.git"
    root = Path(cache_dir or (Path.home() / ".repoforge" / "workspaces")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    destination = root / f"{owner}-{repo}"

    if destination.exists() or destination.is_symlink():
        if destination.is_symlink():
            raise ValueError(f"Cached workspace must not be a symlink: {destination}")
        if not (destination / ".git").exists():
            raise FileExistsError(
                f"Workspace path exists but is not a Git repository: {destination}"
            )
        result = subprocess.run(
            ["git", "-C", str(destination), "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        existing_remote = result.stdout.strip().removesuffix(".git").lower()
        expected_remote = remote.removesuffix(".git").lower()
        if result.returncode != 0 or existing_remote != expected_remote:
            raise ValueError(f"Cached workspace origin does not match {remote}")
        resolved_destination = destination.resolve(strict=True)
        try:
            resolved_destination.relative_to(root)
        except ValueError as exc:
            raise ValueError("Cached workspace resolves outside the cache directory") from exc
        return RepositoryTarget(reference, resolved_destination, True, remote)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--", remote, str(destination)],
            check=True,
            capture_output=True,
            text=True,
            timeout=clone_timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git is required to clone remote repositories") from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(destination, ignore_errors=True)
        detail = (exc.stderr or exc.stdout or "git clone failed").strip()
        raise RuntimeError(f"Could not clone {remote}: {detail}") from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError(f"Cloning {remote} exceeded {clone_timeout} seconds") from exc

    return RepositoryTarget(reference, destination.resolve(), True, remote)


def collect_repository_context(
    repository: str | Path,
    *,
    max_files: int = 24,
    max_file_chars: int = 8_000,
    max_total_chars: int = 48_000,
) -> dict[str, object]:
    """Collect bounded, text-only context while excluding secrets and generated folders."""
    root = Path(repository).resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise ValueError("A local Git repository directory is required")
    if max_files < 1 or max_file_chars < 1 or max_total_chars < 1:
        raise ValueError("Context limits must be positive")

    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if tracked.returncode == 0:
        candidates = sorted(set(tracked.stdout.splitlines()))
    else:
        candidates = []
        for current, dirs, filenames in os.walk(root, followlinks=False):
            dirs[:] = sorted(
                name for name in dirs
                if name not in _SKIP_DIRS and not (Path(current) / name).is_symlink()
            )
            for filename in filenames:
                candidates.append((Path(current) / filename).relative_to(root).as_posix())
        candidates.sort()

    safe_paths: list[str] = []
    for relative in candidates:
        path = Path(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(part in _SKIP_DIRS for part in path.parts)
        ):
            continue
        name = path.name.lower()
        if (
            name.startswith(".env")
            or name in _SECRET_NAMES
            or "secret" in name
            or "credential" in name
            or name in {".npmrc", ".pypirc", ".netrc"}
        ):
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES or name.endswith((".min.js", ".min.css")):
            continue
        absolute = root / path
        if absolute.is_symlink() or not absolute.is_file():
            continue
        try:
            absolute.resolve(strict=True).relative_to(root)
        except (OSError, ValueError):
            continue
        safe_paths.append(path.as_posix())

    priority_names = {
        "readme.md", "pyproject.toml", "package.json", "requirements.txt",
        "go.mod", "cargo.toml", "pom.xml", "build.gradle", "composer.json",
        "gemfile", "makefile", "dockerfile",
    }
    safe_paths.sort(key=lambda item: (Path(item).name.lower() not in priority_names, item))
    selected = safe_paths[:max_files]
    files: dict[str, str] = {}
    total_chars = 0
    languages: dict[str, int] = {}

    for relative in safe_paths:
        suffix = Path(relative).suffix.lower()
        language = _LANGUAGE_BY_SUFFIX.get(suffix)
        if language:
            languages[language] = languages.get(language, 0) + 1

    for relative in selected:
        path = root / relative
        try:
            if path.stat().st_size > max_file_chars * 4:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\x00" in text:
            continue
        remaining = max_total_chars - total_chars
        if remaining <= 0:
            break
        excerpt = text[: min(max_file_chars, remaining)]
        marker = "\n[context excerpt truncated]"
        if len(text) > len(excerpt) and len(excerpt) + len(marker) <= remaining:
            excerpt += marker
        files[relative] = excerpt
        total_chars += len(excerpt)

    return {
        "repository_name": root.name,
        "repository_path": str(root),
        "file_count": len(safe_paths),
        "languages": dict(sorted(languages.items())),
        "file_tree": safe_paths[:200],
        "files": files,
        "context_truncated": len(files) < len(safe_paths) or total_chars >= max_total_chars,
    }
