from pathlib import Path
from ..orchestrator import AIOrchestrator
from ..forge import RepoScanner

class READMEGenerator:
    """Generates README files"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.orchestrator = AIOrchestrator()
        self.scanner = RepoScanner(repo_path)
    
    def generate(self) -> str:
        """Generate README content"""
        analysis = self.scanner.analyze()
        
        prompt = f"""Generate a professional README.md for this project:

Project Analysis:
- Languages: {analysis['languages']}
- Stats: {analysis['stats']}
- Structure: {list(analysis['structure'].keys())[:10]}

Include:
1. Project title and description
2. Features
3. Installation instructions
4. Usage examples
5. Project structure
6. Contributing guidelines
7. License

Make it professional and well-formatted in Markdown."""
        
        return self.orchestrator.generate(prompt, task_type="documentation")
    
    def save(self, output_path: str = None):
        """Generate and save README"""
        readme = self.generate()
        output = output_path or (self.repo_path / 'README.md')
        
        with open(output, 'w') as f:
            f.write(readme)
        
        return output