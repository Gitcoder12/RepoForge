import ast
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("RepoForge.Validator")

class ThreatVisitor(ast.NodeVisitor):
    """Parses Python AST to find malicious logic (Rogue AI Defense)."""
    def __init__(self):
        self.threats = []

    def visit_Call(self, node):
        # 1. Block Dynamic Execution
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "__import__"):
                self.threats.append(f"CRITICAL: Rogue execution '{node.func.id}()' at line {node.lineno}")
        
        # 2. Block Network Exfiltration (Egress)
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id in ("requests", "urllib", "socket", "http"):
                    self.threats.append(f"CRITICAL: Data exfiltration attempt via '{node.func.value.id}.{node.func.attr}' at line {node.lineno}")
            
            # 3. Block Destructive Actions
            if node.func.value.id in ("os", "subprocess", "shutil"):
                if node.func.attr in ("system", "popen", "call", "run", "remove", "rmtree", "unlink"):
                    self.threats.append(f"CRITICAL: Destructive action '{node.func.value.id}.{node.func.attr}()' at line {node.lineno}")

        self.generic_visit(node)

class Validator:
    IGNORE_DIRS = {".git", ".repoforge", "__pycache__", "node_modules", "venv", ".venv", "dist", "build"}

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()

    def _check_syntax(self, file_path: Path) -> Dict[str, Any]:
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            if not source.strip():
                return {"file": str(file_path.relative_to(self.repo_path)), "passed": True}
                
            tree = ast.parse(source)
            
            # ROGUE AI BLOCKER
            visitor = ThreatVisitor()
            visitor.visit(tree)
            if visitor.threats:
                logger.critical(f"🚨 MALWARE DETECTED in {file_path.name}: {visitor.threats}")
                return {"file": str(file_path.relative_to(self.repo_path)), "passed": False, "threats": visitor.threats}
                
            return {"file": str(file_path.relative_to(self.repo_path)), "passed": True}
        except SyntaxError as e:
            logger.error(f"Syntax Error in {file_path.name}: line {e.lineno}: {e.msg}")
            return {"file": str(file_path.relative_to(self.repo_path)), "passed": False, "error": f"line {e.lineno}: {e.msg}"}
        except Exception as e:
            logger.warning(f"Could not validate {file_path.name}: {e}")
            return {"file": str(file_path.relative_to(self.repo_path)), "passed": True, "warning": str(e)}

    async def validate(self, target_files: List[str] = None) -> Dict[str, Any]:
        logger.info(f"🛡️ Deploying The Shield... (Targets: {len(target_files) if target_files else 'All'})")
        
        results = []
        syntax_errors = 0
        malware_threats = 0

        if target_files:
            for tf in target_files:
                fp = self.repo_path / tf
                if fp.exists() and fp.suffix == ".py":
                    res = self._check_syntax(fp)
                    results.append(res)
                    if not res["passed"]:
                        if "threats" in res: malware_threats += 1
                        else: syntax_errors += 1
        else:
            for file in self.repo_path.rglob("*.py"):
                if any(part in self.IGNORE_DIRS for part in file.parts): continue
                res = self._check_syntax(file)
                results.append(res)
                if not res["passed"]:
                    if "threats" in res: malware_threats += 1
                    else: syntax_errors += 1

        if malware_threats > 0:
            logger.critical(f"🛑 QUARANTINE INITIATED! {malware_threats} malicious threats found.")
            return {"passed": False, "reason": "malware_detected", "results": results}

        if syntax_errors > 0:
            logger.error(f"❌ Validation FAILED: {syntax_errors} syntax errors.")
            return {"passed": False, "reason": "syntax_errors", "results": results}

        logger.info("🏃 Running pytest suite...")
        try:
            process = await asyncio.create_subprocess_exec(
                "pytest", "--tb=short", "-q", cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if process.returncode != 0:
                logger.error("❌ Tests FAILED.")
                return {"passed": False, "reason": "test_failures", "output": stdout.decode()[:500]}
        except FileNotFoundError:
            logger.warning("Pytest not found. Skipping test execution.")

        logger.info("✅ SHIELD ACTIVATED: Code is secure.")
        return {"passed": True, "results": results}

RepoValidator = Validator
