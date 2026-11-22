"""Build a compact, dependency-aware symbol index for mixed-language repositories.

The index is structural metadata, not a source-code substitute or a security verdict.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import posixpath
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_FILE_BYTES = 1_000_000
MAX_CACHE_BYTES = 20_000_000

LANGUAGES = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
}
IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".next",
    ".nuxt",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
    ".repoforge",
}
JS_IMPORT = re.compile(
    r"""(?m)^\s*import\s+(?:[^;\n]*?\s+from\s+)?["']([^"']+)["']"""
)
JS_EXPORT_FROM = re.compile(r"""(?m)^\s*export\s+[^;\n]*?\s+from\s+["']([^"']+)["']""")
JS_DYNAMIC_IMPORT = re.compile(r"""\b(?:require|import)\s*\(\s*["']([^"']+)["']\s*\)""")
JS_FUNCTION = re.compile(
    r"(?m)^\s*(?:(?:export|default|async)\s+)*function\s*\*?\s*"
    r"([A-Za-z_$][\w$]*)\s*\("
)
JS_CLASS = re.compile(
    r"(?m)^\s*(?:(?:export|default|abstract)\s+)*class\s+([A-Za-z_$][\w$]*)\b"
)
JS_VARIABLE = re.compile(
    r"(?m)^\s*(?:(?:export|default)\s+)*(const|let|var)\s+([A-Za-z_$][\w$]*)\b"
)
GO_FUNCTION = re.compile(
    r"(?m)^\s*func\s+(?:\([^\n)]*\)\s*)?([A-Za-z_]\w*)\s*\("
)
GO_TYPE = re.compile(r"(?m)^\s*type\s+([A-Za-z_]\w*)\s+")
GO_CONST = re.compile(r"(?m)^\s*const\s+([A-Za-z_]\w*)\b")
GO_IMPORT_DECL = re.compile(
    r'(?m)^\s*import\s+(?:\(\s*([\s\S]*?)\s*\)|"([^"]+)")'
)
GO_QUOTED_IMPORT = re.compile(r'"([^"]+)"')
GO_MODULE = re.compile(r"(?m)^\s*module\s+([^\s]+)")


class CodebaseIndexer:
    """Index Python, JavaScript/TypeScript, and Go files without executing them."""

    def __init__(
        self,
        repo_path: str | Path,
        *,
        max_files: int = DEFAULT_MAX_FILES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ) -> None:
        self.root = Path(repo_path).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"repository path is not a directory: {self.root}")
        if max_files < 1:
            raise ValueError("max_files must be at least 1")
        if max_file_bytes < 1:
            raise ValueError("max_file_bytes must be at least 1")
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes

    def _discover(self) -> tuple[list[tuple[str, Path, os.stat_result]], list[dict[str, Any]]]:
        candidates: list[tuple[str, Path, os.stat_result]] = []
        inventory: list[dict[str, Any]] = []
        for current, directories, filenames in os.walk(
            self.root, topdown=True, followlinks=False
        ):
            current_path = Path(current)
            directories[:] = sorted(
                name
                for name in directories
                if name.casefold() not in IGNORED_DIRECTORIES
                and not (current_path / name).is_symlink()
            )
            for filename in filenames:
                candidate = current_path / filename
                language = LANGUAGES.get(candidate.suffix.casefold())
                if language is None or filename.casefold() == "repo_dictionary.json":
                    continue
                if candidate.is_symlink():
                    continue
                try:
                    resolved = candidate.resolve(strict=True)
                    resolved.relative_to(self.root)
                    stat = resolved.stat()
                except (OSError, RuntimeError, ValueError):
                    continue
                if not resolved.is_file():
                    continue
                relative = resolved.relative_to(self.root).as_posix()
                candidates.append((relative, resolved, stat))
        candidates.sort(key=lambda item: item[0])
        for relative, _, stat in candidates:
            inventory.append(
                {
                    "path": relative,
                    "size_bytes": stat.st_size,
                    "modified_ns": stat.st_mtime_ns,
                }
            )
        return candidates, inventory

    @staticmethod
    def _line_signature(source: str, line: int) -> str:
        lines = source.splitlines()
        if 1 <= line <= len(lines):
            return lines[line - 1].strip()[:240]
        return ""

    @staticmethod
    def _add_symbol(
        symbols: list[dict[str, Any]],
        *,
        kind: str,
        name: str,
        line: int,
        end_line: int | None = None,
        signature: str = "",
        module: str | None = None,
    ) -> None:
        item: dict[str, Any] = {
            "kind": kind,
            "name": name,
            "line": line,
            "end_line": end_line or line,
        }
        if signature:
            item["signature"] = signature
        if module is not None:
            item["module"] = module
        symbols.append(item)

    def _extract_python(
        self, source: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
        symbols: list[dict[str, Any]] = []
        imports: list[dict[str, Any]] = []
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return symbols, imports, f"line {exc.lineno or 1}: {exc.msg}"

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._add_symbol(
                    symbols,
                    kind="class",
                    name=node.name,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=self._line_signature(source, node.lineno),
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_symbol(
                    symbols,
                    kind="function",
                    name=node.name,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=self._line_signature(source, node.lineno),
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {"module": alias.name, "names": [alias.asname or alias.name], "line": node.lineno}
                    )
                    self._add_symbol(
                        symbols,
                        kind="import",
                        name=alias.asname or alias.name,
                        line=node.lineno,
                        module=alias.name,
                        signature=self._line_signature(source, node.lineno),
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append(
                    {
                        "module": module,
                        "level": node.level,
                        "names": names,
                        "line": node.lineno,
                    }
                )
                for alias in node.names:
                    self._add_symbol(
                        symbols,
                        kind="import",
                        name=alias.asname or alias.name,
                        line=node.lineno,
                        module=("." * node.level) + module,
                        signature=self._line_signature(source, node.lineno),
                    )
        return self._sort_symbols(symbols), self._sort_imports(imports), None

    def _extract_javascript(
        self, source: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], None]:
        symbols: list[dict[str, Any]] = []
        imports: list[dict[str, Any]] = []
        for pattern, kind in ((JS_FUNCTION, "function"), (JS_CLASS, "class")):
            for match in pattern.finditer(source):
                line = source.count("\n", 0, match.start()) + 1
                name = match.group(1)
                self._add_symbol(
                    symbols,
                    kind=kind,
                    name=name,
                    line=line,
                    signature=self._line_signature(source, line),
                )
        for match in JS_VARIABLE.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            self._add_symbol(
                symbols,
                kind="constant" if match.group(1) == "const" else "variable",
                name=match.group(2),
                line=line,
                signature=self._line_signature(source, line),
            )
        import_matches = list(JS_IMPORT.finditer(source)) + list(JS_EXPORT_FROM.finditer(source))
        import_matches.extend(JS_DYNAMIC_IMPORT.finditer(source))
        for match in import_matches:
            module = match.group(1)
            line = source.count("\n", 0, match.start()) + 1
            imports.append({"module": module, "line": line, "names": []})
            self._add_symbol(
                symbols,
                kind="import",
                name=module,
                line=line,
                module=module,
                signature=self._line_signature(source, line),
            )
        return self._sort_symbols(symbols), self._sort_imports(imports), None

    def _extract_go(
        self, source: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], None]:
        symbols: list[dict[str, Any]] = []
        imports: list[dict[str, Any]] = []
        for pattern, kind in ((GO_FUNCTION, "function"), (GO_TYPE, "type"), (GO_CONST, "constant")):
            for match in pattern.finditer(source):
                line = source.count("\n", 0, match.start()) + 1
                self._add_symbol(
                    symbols,
                    kind=kind,
                    name=match.group(1),
                    line=line,
                    signature=self._line_signature(source, line),
                )
        for match in GO_IMPORT_DECL.finditer(source):
            block = match.group(1) or match.group(2) or ""
            for quoted in GO_QUOTED_IMPORT.finditer(block):
                module = quoted.group(1)
                line = source.count("\n", 0, match.start() + quoted.start()) + 1
                imports.append({"module": module, "line": line, "names": []})
                self._add_symbol(
                    symbols,
                    kind="import",
                    name=module,
                    line=line,
                    module=module,
                    signature=self._line_signature(source, line),
                )
        return self._sort_symbols(symbols), self._sort_imports(imports), None

    @staticmethod
    def _sort_symbols(symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: dict[tuple[Any, ...], dict[str, Any]] = {}
        for item in symbols:
            key = (item["kind"], item["name"], item["line"])
            unique[key] = item
        return sorted(unique.values(), key=lambda item: (item["line"], item["kind"], item["name"]))

    @staticmethod
    def _sort_imports(imports: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique = {
            (item["module"], item["line"], tuple(item.get("names", [])), item.get("level", 0)): item
            for item in imports
        }
        return sorted(unique.values(), key=lambda item: (item["line"], item["module"]))

    def _go_module_path(self) -> str | None:
        module_file = self.root / "go.mod"
        try:
            if module_file.is_symlink() or module_file.stat().st_size > 100_000:
                return None
            match = GO_MODULE.search(module_file.read_text(encoding="utf-8"))
            return match.group(1) if match else None
        except (OSError, UnicodeError):
            return None

    @staticmethod
    def _resolve_python_import(
        current: str,
        spec: dict[str, Any],
        indexed_paths: set[str],
    ) -> set[str]:
        module = str(spec.get("module", ""))
        level = int(spec.get("level", 0))
        names = [name for name in spec.get("names", []) if name and name != "*"]
        if level:
            parent = list(Path(current).parent.parts)
            remove_count = max(level - 1, 0)
            if remove_count > len(parent):
                return set()
            base_parts = parent[: len(parent) - remove_count]
            module_parts = [part for part in module.split(".") if part]
            base_parts.extend(module_parts)
            bases = [Path(*base_parts).as_posix() if base_parts else ""]
            if not module_parts:
                bases.extend(
                    (Path(*base_parts, name).as_posix() if base_parts else name)
                    for name in names
                )
        else:
            base_parts = [part for part in module.split(".") if part]
            bases = [Path(*base_parts).as_posix()] if base_parts else []
            bases.extend(Path(*base_parts, name).as_posix() for name in names if base_parts)

        resolved: set[str] = set()
        for base in bases:
            candidates = {f"{base}.py", f"{base}.pyi", f"{base}/__init__.py"}
            resolved.update(candidates.intersection(indexed_paths))
        resolved.discard(current)
        return resolved

    @staticmethod
    def _resolve_javascript_import(
        current: str, module: str, indexed_paths: set[str]
    ) -> set[str]:
        if not module.startswith("."):
            return set()
        base = posixpath.normpath(posixpath.join(posixpath.dirname(current), module))
        if base == ".." or base.startswith("../") or base.startswith("/"):
            return set()
        candidates = {base}
        suffixes = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
        if not Path(base).suffix:
            candidates.update(base + suffix for suffix in suffixes)
            candidates.update(posixpath.join(base, "index" + suffix) for suffix in suffixes)
        return candidates.intersection(indexed_paths)

    @staticmethod
    def _resolve_go_import(
        module: str, go_module: str | None, package_files: dict[str, list[str]]
    ) -> set[str]:
        if not go_module or not (module == go_module or module.startswith(go_module + "/")):
            return set()
        suffix = module[len(go_module) :].lstrip("/")
        package = PurePosixPath(suffix).as_posix() if suffix else "."
        return set(package_files.get(package, []))

    def build(self) -> dict[str, Any]:
        """Create a fresh structural index. Repository source files are never modified."""
        candidates, inventory = self._discover()
        indexed_candidates = candidates[: self.max_files]
        indexed_paths: set[str] = set()
        files: list[dict[str, Any]] = []
        skipped_files = max(0, len(candidates) - len(indexed_candidates))
        parse_errors = 0

        for relative, path, stat in indexed_candidates:
            if stat.st_size > self.max_file_bytes:
                skipped_files += 1
                continue
            try:
                raw = path.read_bytes()
                source = raw.decode("utf-8")
            except (OSError, UnicodeError):
                skipped_files += 1
                continue
            if b"\x00" in raw:
                skipped_files += 1
                continue

            language = LANGUAGES[path.suffix.casefold()]
            if language == "python":
                symbols, imports, parse_error = self._extract_python(source)
            elif language in {"javascript", "typescript"}:
                symbols, imports, parse_error = self._extract_javascript(source)
            else:
                symbols, imports, parse_error = self._extract_go(source)
            if parse_error:
                parse_errors += 1
            indexed_paths.add(relative)
            item: dict[str, Any] = {
                "path": relative,
                "language": language,
                "size_bytes": len(raw),
                "modified_ns": stat.st_mtime_ns,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "symbols": symbols,
                "imports": imports,
            }
            if parse_error:
                item["parse_error"] = parse_error
            files.append(item)

        indexed_paths = {item["path"] for item in files}
        go_module = self._go_module_path()
        go_packages: dict[str, list[str]] = {}
        for item in files:
            if item["language"] == "go":
                package = Path(item["path"]).parent.as_posix()
                if package == ".":
                    package = "."
                go_packages.setdefault(package, []).append(item["path"])

        dependencies: dict[str, list[str]] = {}
        for item in files:
            current = item["path"]
            resolved: set[str] = set()
            for spec in item["imports"]:
                if item["language"] == "python":
                    resolved.update(self._resolve_python_import(current, spec, indexed_paths))
                elif item["language"] in {"javascript", "typescript"}:
                    resolved.update(
                        self._resolve_javascript_import(current, spec["module"], indexed_paths)
                    )
                elif item["language"] == "go":
                    resolved.update(
                        self._resolve_go_import(spec["module"], go_module, go_packages)
                    )
            resolved.discard(current)
            dependencies[current] = sorted(resolved)

        language_counts: dict[str, int] = {}
        symbol_count = 0
        import_count = 0
        for item in files:
            language_counts[item["language"]] = language_counts.get(item["language"], 0) + 1
            symbol_count += len(item["symbols"])
            import_count += len(item["imports"])
        dependency_edges = sum(len(targets) for targets in dependencies.values())

        repository_id = hashlib.sha256(
            self.root.as_posix().casefold().encode("utf-8")
        ).hexdigest()[:16]
        return {
            "schema_version": SCHEMA_VERSION,
            "repository": self.root.name,
            "repository_id": repository_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "languages": dict(sorted(language_counts.items())),
            "summary": {
                "candidate_files": len(candidates),
                "indexed_files": len(files),
                "skipped_files": skipped_files,
                "parse_errors": parse_errors,
                "symbols": symbol_count,
                "imports": import_count,
                "dependency_edges": dependency_edges,
                "truncated": len(candidates) > self.max_files,
            },
            "inventory": inventory,
            "files": sorted(files, key=lambda item: item["path"]),
            "dependencies": dict(sorted(dependencies.items())),
        }

    def load_cached(self, cache_path: str | Path | None = None) -> dict[str, Any] | None:
        """Load a CLI-generated dictionary only when its source-file inventory is fresh."""
        path = Path(cache_path) if cache_path is not None else self.root / "repo_dictionary.json"
        if path.is_symlink() or not path.is_file():
            return None
        try:
            if path.stat().st_size > MAX_CACHE_BYTES:
                return None
            cached = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if (
            not isinstance(cached, dict)
            or cached.get("schema_version") != SCHEMA_VERSION
            or cached.get("repository") != self.root.name
            or cached.get("repository_id")
            != hashlib.sha256(self.root.as_posix().casefold().encode("utf-8")).hexdigest()[:16]
            or not isinstance(cached.get("files"), list)
            or not isinstance(cached.get("inventory"), list)
            or not isinstance(cached.get("dependencies"), dict)
            or any(
                not isinstance(item, dict)
                or not isinstance(item.get("path"), str)
                or not isinstance(item.get("symbols"), list)
                or not isinstance(item.get("imports"), list)
                for item in cached.get("files", [])
            )
            or any(
                not isinstance(path_item, str)
                or not isinstance(targets, list)
                or any(not isinstance(target, str) for target in targets)
                for path_item, targets in cached.get("dependencies", {}).items()
            )
        ):
            return None
        _, current_inventory = self._discover()
        if cached["inventory"] != current_inventory:
            return None
        return cached

    @staticmethod
    def write_json(index: dict[str, Any], output_path: str | Path) -> Path:
        """Atomically write an index JSON file, refusing to replace a symlink."""
        destination = Path(output_path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            raise ValueError(f"refusing to write through a symlink: {destination}")
        destination = destination.resolve()
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".repoforge-index-",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as handle:
                temporary_path = handle.name
                json.dump(index, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(temporary_path, destination)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return destination
