import ast
import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("RepoForge.Validator")


class ThreatVisitor(ast.NodeVisitor):
    """Conservative AST checks for dynamic execution and risky operations."""

    def __init__(self) -> None:
        self.threats: list[str] = []

    @staticmethod
    def _root_name(node: ast.AST) -> str | None:
        while isinstance(node, ast.Attribute):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    def visit_Call(self, node: ast.Call) -> None:
        function = node.func
        if isinstance(function, ast.Name):
            if function.id in ("eval", "exec", "__import__"):
                self.threats.append(
                    f"CRITICAL: Dynamic execution '{function.id}()' at line {node.lineno}"
                )

        elif isinstance(function, ast.Attribute):
            root = self._root_name(function.value)
            attribute = function.attr
            if root in ("requests", "urllib", "socket", "http"):
                self.threats.append(
                    f"REVIEW: Network operation '{root}.{attribute}' at line {node.lineno}"
                )
            if root in ("os", "subprocess", "shutil") and attribute in (
                "system", "popen", "call", "run", "remove", "rmtree", "unlink"
            ):
                self.threats.append(
                    f"REVIEW: Potentially destructive operation "
                    f"'{root}.{attribute}()' at line {node.lineno}"
                )

        self.generic_visit(node)


class Validator:
    IGNORE_DIRS = {
        ".git", ".repoforge", "__pycache__", "node_modules",
        "venv", ".venv", "dist", "build",
    }

    def __init__(self, repo_path: str = ".") -> None:
        self.repo_path = Path(repo_path).resolve()

    def _resolve_target(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("absolute validation paths are not allowed")
        resolved = (self.repo_path / candidate).resolve()
        try:
            resolved.relative_to(self.repo_path)
        except ValueError as exc:
            raise ValueError("validation path escapes repository root") from exc
        return resolved

    def _check_syntax(self, file_path: Path) -> dict[str, Any]:
        relative = str(file_path.relative_to(self.repo_path))
        try:
            source = file_path.read_text(encoding="utf-8")
            if not source.strip():
                return {"file": relative, "passed": True}

            tree = ast.parse(source)
            visitor = ThreatVisitor()
            visitor.visit(tree)
            if visitor.threats:
                logger.warning("Review-required operations in %s: %s", relative, visitor.threats)
                return {"file": relative, "passed": False, "threats": visitor.threats}
            return {"file": relative, "passed": True}

        except SyntaxError as exc:
            logger.error("Syntax error in %s at line %s: %s", relative, exc.lineno, exc.msg)
            return {
                "file": relative,
                "passed": False,
                "error": f"line {exc.lineno}: {exc.msg}",
            }
        except Exception as exc:
            logger.exception("Could not validate %s", relative)
            return {"file": relative, "passed": False, "error": str(exc)}

    async def validate(self, target_files: list[str] | None = None) -> dict[str, Any]:
        logger.info(
            "Validating Python files (targets=%s)",
            len(target_files) if target_files is not None else "all",
        )
        results = []
        invalid_paths = []

        if target_files is not None:
            candidates = []
            for target in target_files:
                try:
                    resolved = self._resolve_target(target)
                except (TypeError, ValueError) as exc:
                    invalid_paths.append({"file": str(target), "error": str(exc)})
                    continue
                if resolved.suffix == ".py" and resolved.is_file():
                    candidates.append(resolved)
        else:
            candidates = [
                path for path in self.repo_path.rglob("*.py")
                if not any(
                    part in self.IGNORE_DIRS
                    for part in path.relative_to(self.repo_path).parts
                )
            ]

        for file_path in candidates:
            results.append(self._check_syntax(file_path))

        failed = [item for item in results if not item["passed"]]
        if invalid_paths or failed:
            return {
                "passed": False,
                "reason": "invalid_paths" if invalid_paths else "validation_failed",
                "results": results,
                "invalid_paths": invalid_paths,
            }

        logger.info("Running pytest suite...")
        try:
            process = await asyncio.create_subprocess_exec(
                "pytest", "--tb=short", "-q",
                cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                return {
                    "passed": False,
                    "reason": "test_failures",
                    "output": (stdout + stderr).decode(errors="replace")[:2000],
                    "results": results,
                }
        except FileNotFoundError:
            return {
                "passed": False,
                "reason": "pytest_unavailable",
                "results": results,
            }

        return {"passed": True, "results": results}


RepoValidator = Validator
