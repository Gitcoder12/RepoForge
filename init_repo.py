import os

# 1. Create directories
os.makedirs("src/repoforge/providers", exist_ok=True)
os.makedirs("src/repoforge/generators", exist_ok=True)
os.makedirs("src/repoforge/workflows", exist_ok=True)

# 2. Write pyproject.toml safely (no nested quotes)
toml_content = """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "repoforge"
version = "0.1.0"
description = "AI Orchestration Platform"
requires-python = ">=3.9"
dependencies = [
    "openai>=1.0.0",
    "anthropic>=0.7.0",
    "google-generativeai>=0.3.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "typer>=0.9.0",
]

[tool.setuptools.packages.find]
where = ["src"]
"""
with open("pyproject.toml", "w", encoding="utf-8") as f:
    f.write(toml_content)

# 3. Write basic Python files
with open("src/repoforge/__init__.py", "w", encoding="utf-8") as f:
    f.write("__version__ = '0.1.0'\n")

with open("src/repoforge/cli.py", "w", encoding="utf-8") as f:
    f.write("import typer\n")
    f.write("app = typer.Typer(help='RepoForge CLI')\n")
    f.write("@app.command()\n")
    f.write("def hello():\n")
    f.write("    print('RepoForge is alive!')\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    app()\n")

print("✅ Clean setup complete!")
print("Next: Run 'pip install -e .'")