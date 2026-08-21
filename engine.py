from typing import Dict, Any, List
from pathlib import Path
import yaml

class WorkflowEngine:
    """Executes automated workflows"""
    
    def __init__(self):
        self.workflows_dir = Path.home() / ".repoforge" / "workflows"
        self.workflows_dir.mkdir(exist_ok=True)
        self.workflows = self._load_workflows()
    
    def _load_workflows(self) -> Dict[str, Any]:
        """Load workflow definitions"""
        workflows = {}
        for wf_file in self.workflows_dir.glob("*.yaml"):
            with open(wf_file, 'r') as f:
                workflows[wf_file.stem] = yaml.safe_load(f)
        return workflows
    
    def run(self, workflow_name: str, context: Dict[str, Any] = None):
        """Run a workflow"""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        context = context or {}
        results = {}
        
        for step in workflow.get("steps", []):
            step_name = step.get("name")
            step_type = step.get("type")
            
            # Execute step based on type
            if step_type == "scan":
                from ..forge import RepoScanner
                scanner = RepoScanner(context.get("repo_path", "."))
                results[step_name] = scanner.analyze()
            
            elif step_type == "generate":
                target = step.get("target")
                if target == "readme":
                    from ..generators import READMEGenerator
                    generator = READMEGenerator(context.get("repo_path", "."))
                    results[step_name] = generator.generate()
            
            elif step_type == "ai":
                from ..orchestrator import AIOrchestrator
                orchestrator = AIOrchestrator()
                prompt = step.get("prompt")
                results[step_name] = orchestrator.generate(prompt)
        
        return results
    
    def create_workflow(self, name: str, steps: List[Dict[str, Any]]):
        """Create a new workflow"""
        workflow = {
            "name": name,
            "steps": steps
        }
        
        workflow_file = self.workflows_dir / f"{name}.yaml"
        with open(workflow_file, 'w') as f:
            yaml.safe_dump(workflow, f, default_flow_style=False)
        
        self.workflows[name] = workflow