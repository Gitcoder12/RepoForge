from pathlib import Path
from ..orchestrator import AIOrchestrator

class DocumentationGenerator:
    """Generates documentation"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.orchestrator = AIOrchestrator()
    
    def generate_api_docs(self, source_files: list) -> str:
        """Generate API documentation"""
        prompt = "Generate API documentation for these files:\n\n"
        
        for file_path in source_files:
            with open(file_path, 'r') as f:
                content = f.read()
                prompt += f"\n\n### {file_path}\n```python\n{content}\n```\n"
        
        prompt += "\nGenerate comprehensive API documentation with examples."
        
        return self.orchestrator.generate(prompt, task_type="documentation")
    
    def generate_architecture_docs(self) -> str:
        """Generate architecture documentation"""
        prompt = f"""Analyze this project structure and generate architecture documentation:

{self._get_project_structure()}

Include:
1. Architecture overview
2. Component descriptions
3. Data flow
4. Design patterns used
5. Dependencies"""
        
        return self.orchestrator.generate(prompt, task_type="documentation")
    
    def _get_project_structure(self) -> str:
        """Get project structure as text"""
        structure = []
        for root, dirs, files in Path(self.repo_path).walk():
            level = root.relative_to(self.repo_path).parts
            indent = '  ' * len(level)
            structure.append(f"{indent}{Path(root).name}/")
            
            subindent = '  ' * (len(level) + 1)
            for file in files[:10]:  # Limit files
                structure.append(f"{subindent}{file}")
        
        return "\n".join(structure[:50])  # Limit output