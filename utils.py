from pathlib import Path
from typing import Optional
import re

def find_project_root(path: Optional[str] = None) -> Path:
    """Find project root directory"""
    current = Path(path or Path.cwd())
    
    indicators = ['.git', 'pyproject.toml', 'setup.py', 'package.json', 'Cargo.toml']
    
    for parent in [current] + list(current.parents):
        for indicator in indicators:
            if (parent / indicator).exists():
                return parent
    
    return current

def detect_language(file_path: Path) -> Optional[str]:
    """Detect programming language from file extension"""
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php'
    }
    
    return extension_map.get(file_path.suffix.lower())

def count_lines(file_path: Path) -> int:
    """Count lines in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0

def extract_code_blocks(text: str) -> list:
    """Extract code blocks from text"""
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang or 'text', code.strip()) for lang, code in matches]