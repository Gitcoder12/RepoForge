import os
import sys
from pathlib import Path

# Ensure we are in the right place
project_root = Path(".").resolve()
execution_dir = project_root / "src" / "repoforge" / "execution"
execution_dir.mkdir(parents=True, exist_ok=True)

# Delete corrupted files if they exist
(execution_dir / "action_runner.py").unlink(missing_ok=True)
(project_root / "src" / "repoforge" / "refiner.py").unlink(missing_ok=True)

# Create action_runner.py
action_runner_content = '''import os
from pathlib import Path
from typing import List, Dict, Any

class ActionRunner:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.executed = []
        self.errors = []

    def run(self, actions: List[str], dry_run: bool = False) -> Dict[str, Any]:
        if not actions:
            return {"status": "no_actions", "executed": [], "errors": []}
        print(f"  📂 Executing {len(actions)} actions in {self.repo_path}")
        for action in actions:
            try:
                self._execute_action(action, dry_run)
            except Exception as e:
                self.errors.append({"action": action, "error": str(e)})
        return {"status": "completed" if not self.errors else "partial", "executed": self.executed, "errors": self.errors}

    def _execute_action(self, action: str, dry_run: bool):
        action = action.strip()
        if action.lower().startswith("create ") or action.lower().startswith("add "):
            parts = action.split(" ", 1)
            if len(parts) == 2:
                filename = parts[1].strip()
                if "directory" in filename.lower():
                    self._create_directory(filename.replace(" directory", "").strip(), dry_run)
                    return
                self._create_file(filename, dry_run)
                return
        if "readme" in action.lower():
            self._create_file("README.md", dry_run, "# Project Name\\n\\n## Description\\nTODO"); return
        if "license" in action.lower():
            self._create_file("LICENSE", dry_run, "MIT License\\n\\nCopyright (c) 2024"); return
        if "contributing" in action.lower():
            self._create_file("CONTRIBUTING.md", dry_run, "# Contributing\\n\\n1. Fork\\n2. PR"); return
        if "pull_request_template" in action.lower():
            self._create_file(".github/PULL_REQUEST_TEMPLATE.md", dry_run, "## Description\\n\\n## Type of Change"); return
        if "issue template" in action.lower():
            self._create_file(".github/ISSUE_TEMPLATE/bug_report.md", dry_run, "---\\nname: Bug report\\n---\\n\\n**Describe**"); return
        if "code_of_conduct" in action.lower():
            self._create_file("CODE_OF_CONDUCT.md", dry_run, "# Code of Conduct\\n\\nBe kind."); return
        if "changelog" in action.lower():
            self._create_file("CHANGELOG.md", dry_run, "# Changelog\\n\\n## [Unreleased]\\n- Initial"); return
        if "github actions" in action.lower():
            self._create_file(".github/workflows/ci.yml", dry_run, "name: CI\\non: [push]\\njobs:\\n  build:\\n    runs-on: ubuntu-latest\\n    steps:\\n      - uses: actions/checkout@v3\\n      - run: echo 'Hello'"); return
        if "dockerfile" in action.lower():
            self._create_file("Dockerfile", dry_run, "FROM python:3.11\\nWORKDIR /app\\nCOPY . .\\nCMD [\\"python\\", \\"main.py\\"]"); return
        if "dependency manifest" in action.lower():
            self._create_file("requirements.txt", dry_run, "# Dependencies go here"); return
        print(f"    ⚠️ Unknown action: {action}")
        self.executed.append({"action": action, "status": "unknown"})

    def _create_file(self, filepath: str, dry_run: bool, content: str = ""):
        full_path = self.repo_path / filepath
        if dry_run:
            print(f"    📄 Would create: {full_path}")
            self.executed.append({"action": f"Create {filepath}", "status": "dry_run"})
            return
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    ✅ Created: {full_path}")
        self.executed.append({"action": f"Create {filepath}", "status": "created"})

    def _create_directory(self, dirname: str, dry_run: bool):
        full_path = self.repo_path / dirname
        if dry_run:
            print(f"    📁 Would create directory: {full_path}")
            self.executed.append({"action": f"Create directory {dirname}", "status": "dry_run"})
            return
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"    ✅ Created directory: {full_path}")
        self.executed.append({"action": f"Create directory {dirname}", "status": "created"})
'''

(execution_dir / "action_runner.py").write_text(action_runner_content, encoding='utf-8')

# Create refiner.py
refiner_content = '''from pathlib import Path
from typing import Dict, Any, List
from .scanner import scan_repository
from .agents.coordinator import AgentCoordinator
from .agents.architect_agent import ArchitectAgent
from .agents.security_agent import SecurityAgent
from .agents.testing_agent import TestingAgent
from .agents.documentation_agent import DocumentationAgent
from .agents.dependency_agent import DependencyAgent
from .agents.performance_agent import PerformanceAgent
from .agents.linting_agent import LintingAgent
from .agents.ci_cd_agent import CICDAgent
from .agents.review_agent import ReviewAgent
from .execution.action_runner import ActionRunner

class Refiner:
    def __init__(self, repo_path: str, provider: str = "openai"):
        self.repo_path = Path(repo_path)
        self.provider = provider

    def refine(self, initial_actions: List[str]) -> Dict[str, Any]:
        print("🔧 Running refinement pass...")
        scan_data = scan_repository(str(self.repo_path))
        coordinator = AgentCoordinator()
        for agent_cls in [ArchitectAgent, SecurityAgent, TestingAgent, DocumentationAgent,
                          DependencyAgent, PerformanceAgent, LintingAgent, CICDAgent, ReviewAgent]:
            try:
                agent = agent_cls(provider=self.provider)
                coordinator.register(agent)
            except:
                pass
        context = {"scan": scan_data, "health": {}, "risk": {}}
        agent_output = coordinator.run(context)
        new_suggestions = agent_output.get("suggestions", [])
        remaining = [s for s in new_suggestions if s not in initial_actions]
        if not remaining:
            return {"status": "no_more_improvements", "executed": []}
        print(f"  🔄 Found {len(remaining)} additional improvements")
        runner = ActionRunner(str(self.repo_path))
        result = runner.run(remaining, dry_run=False)
        return {"status": "refined", "executed": result.get("executed", []), "errors": result.get("errors", [])}
'''

(project_root / "src" / "repoforge" / "refiner.py").write_text(refiner_content, encoding='utf-8')

# Also create __init__.py in execution if missing
(execution_dir / "__init__.py").write_text("", encoding='utf-8')

print("✅ Files recreated cleanly. Run the test command now.")