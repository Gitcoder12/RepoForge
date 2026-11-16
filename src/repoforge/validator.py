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
                "system",
                "popen",
                "call",
                "run",
                "remove",
                "rmtree",
                "unlink",
            ):
                self.threats.append(
                    f"REVIEW: Potentially destructive operation "
                    f"'{root}.{attribute}()' at line {node.lineno}"
                )

        self.generic_visit(node)


class Validator:
    """Static Python checks with opt-in, time-limited target test execution.

    Target-repository tests are arbitrary code. They are not launched unless
    the caller explicitly sets run_tests=True. This is an opt-in safeguard,
    not an operating-system sandbox; only run tests for repositories you trust.
    """

    IGNORE_DIRS = {
        ".git",
        ".repoforge",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
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

    async def validate(
        self,
        target_files: list[str] | None = None,
        *,
        run_tests: bool = False,
        test_timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Validate Python syntax; run pytest only after explicit opt-in.

        Args:
            target_files: Optional repository-relative Python file paths.
            run_tests: Explicitly allow execution of the target repository's tests.
            test_timeout: Maximum seconds to wait for pytest when enabled.
        """
        if not isinstance(run_tests, bool):
            raise ValueError("run_tests must be a boolean")
        if (
            isinstance(test_timeout, bool)
            or not isinstance(test_timeout, (int, float))
            or test_timeout <= 0
        ):
            raise ValueError("test_timeout must be a positive number")

        logger.info(
            "Validating Python files (targets=%s)",
            len(target_files) if target_files is not None else "all",
        )
        results: list[dict[str, Any]] = []
        invalid_paths: list[dict[str, str]] = []

        if target_files is not None:
            candidates: list[Path] = []
            for target in target_files:
                try:
                    resolved = self._resolve_target(target)
                    if resolved.suffix != ".py":
                        raise ValueError("validation target must be a Python (.py) file")
                    if not resolved.is_file():
                        raise ValueError("validation target does not exist or is not a file")
                    candidates.append(resolved)
                except (TypeError, ValueError, OSError, RuntimeError) as exc:
                    invalid_paths.append({"file": str(target), "error": str(exc)})
        else:
            candidates = []
            for path in self.repo_path.rglob("*.py"):
                relative = path.relative_to(self.repo_path)
                if any(part in self.IGNORE_DIRS for part in relative.parts):
                    continue
                try:
                    resolved = path.resolve(strict=True)
                    resolved.relative_to(self.repo_path)
                    if not resolved.is_file():
                        raise ValueError("not a regular file")
                except (OSError, ValueError, RuntimeError):
                    invalid_paths.append(
                        {
                            "file": str(relative),
                            "error": "file path resolves outside repository root or is unreadable",
                        }
                    )
                    continue
                candidates.append(resolved)

        for file_path in candidates:
            results.append(self._check_syntax(file_path))

        failed = [item for item in results if not item["passed"]]
        if invalid_paths or failed:
            return {
                "passed": False,
                "reason": "invalid_paths" if invalid_paths else "validation_failed",
                "results": results,
                "invalid_paths": invalid_paths,
                "test_run": {"status": "not_started"},
            }

        if not run_tests:
            return {
                "passed": True,
                "results": results,
                "test_run": {
                    "status": "skipped",
                    "reason": "target tests execute repository code; pass run_tests=True to opt in",
                },
            }

        logger.warning(
            "Executing tests in %s. This is not a sandbox; run only trusted repositories.",
            self.repo_path,
        )
        try:
            process = await asyncio.create_subprocess_exec(
                "pytest",
                "--tb=short",
                "-q",
                cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=float(test_timeout)
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.communicate()
                return {
                    "passed": False,
                    "reason": "test_timeout",
                    "results": results,
                    "test_run": {
                        "status": "timed_out",
                        "timeout_seconds": float(test_timeout),
                    },
                }
            output = (stdout + stderr).decode(errors="replace")
            if process.returncode != 0:
                return {
                    "passed": False,
                    "reason": "test_failures",
                    "output": output[-8000:],
                    "results": results,
                    "test_run": {"status": "failed"},
                }
        except FileNotFoundError:
            return {
                "passed": False,
                "reason": "pytest_unavailable",
                "results": results,
                "test_run": {"status": "unavailable"},
            }

        return {
            "passed": True,
            "results": results,
            "test_run": {"status": "passed", "output": output[-8000:]},
        }


RepoValidator = Validator
