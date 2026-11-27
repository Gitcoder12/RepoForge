"""Conservative dependency pruning for Python container build contexts.

Only dependencies proven unused by a static import scan are candidates for removal.
Unknown imports, dynamic imports, editable/local dependencies, and unsupported manifests
force conservative retention. This produces a candidate manifest; it does not build images.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable

IMPORT_TO_DISTRIBUTION = {
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "Crypto": "pycryptodome",
}

def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()

def _requirements(path: Path) -> list[str]:
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-r ", "--")):
            continue
        if line.startswith(("-e ", ".", "/")) or " @ " in line:
            raise ValueError("Editable, local, and direct-URL requirements require full retention.")
        match = re.match(r"([A-Za-z0-9][A-Za-z0-9_.-]*)", line)
        if not match:
            raise ValueError(f"Unsupported requirement syntax: {line}")
        entries.append((match.group(1), line))
    return entries

def _imports(root: Path) -> tuple[set[str], bool]:
    found: set[str] = set()
    uncertain = False
    for path in root.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}
               for part in path.parts):
            continue
        if path.is_symlink():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            uncertain = True
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "__import__":
                    uncertain = True
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "import_module":
                    uncertain = True
    return found, uncertain

def prune_requirements(repository: str | Path, manifest: str = "requirements.txt") -> dict[str, object]:
    """Return a conservative candidate requirements list and audit metadata."""
    root = Path(repository).resolve()
    manifest_path = root / manifest
    if not root.is_dir() or not manifest_path.is_file():
        raise ValueError("repository and dependency manifest must exist")
    requirements = _requirements(manifest_path)
    imports, uncertain = _imports(root)
    required_imports = {item.casefold() for item in imports}
    candidates = []
    retained = []
    removed = []
    for distribution, original in requirements:
        mapped = IMPORT_TO_DISTRIBUTION.get(distribution, distribution)
        # Distribution names are not always import names. Unknown mapping is retained.
        import_name = next((key for key, value in IMPORT_TO_DISTRIBUTION.items()
                            if _canonical(value) == _canonical(distribution)), distribution)
        used = import_name.casefold() in required_imports
        known_mapping = (import_name != distribution or distribution.casefold() in required_imports)
        if uncertain or not known_mapping or used:
            retained.append(original)
        else:
            removed.append(original)
    return {
        "manifest": manifest,
        "mode": "conservative_static_candidate",
        "imports": sorted(imports),
        "dynamic_imports_detected": uncertain,
        "retained": retained,
        "removal_candidates": removed,
        "safe_to_prune": not uncertain and not removed is False,
        "warning": "Review candidate output and run clean-image tests; static imports miss plugins and runtime-loaded dependencies.",
    }

def write_pruned_requirements(repository: str | Path, output: str = "requirements.pruned.txt",
                              manifest: str = "requirements.txt") -> dict[str, object]:
    root = Path(repository).resolve()
    result = prune_requirements(root, manifest)
    destination = root / output
    destination.write_text("\n".join(result["retained"]) + "\n", encoding="utf-8")
    result["output"] = destination.relative_to(root).as_posix()
    return result
