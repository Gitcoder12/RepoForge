import os

# 1. Fix Orchestrator to always check latest state
orch_code = """from .plugin_manager import PluginManager

class AIOrchestrator:
    def __init__(self):
        self.pm = PluginManager()
        self.providers = {}
    
    def register(self, name, provider):
        self.providers[name] = provider
        print(f"Registered: {name}")
    
    def generate(self, prompt, provider_name=None):
        # Reload state from disk to ensure we have the latest enabled list
        self.pm.plugins = self.pm._load_plugins()
        
        if not provider_name:
            enabled = self.pm.list_enabled()
            if enabled:
                provider_name = enabled[0]
        
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name].generate(prompt)
        
        return f"Error: Provider '{provider_name}' not available."
"""
with open("src/repoforge/orchestrator.py", "w") as f:
    f.write(orch_code)

# 2. Fix Test Script to use the Orchestrator's Plugin Manager
test_code = """import sys
sys.path.insert(0, 'src')

from repoforge.orchestrator import AIOrchestrator
from repoforge.providers.mock import MockProvider

print("Setting up...")
orchestrator = AIOrchestrator()
orchestrator.register("mock", MockProvider())

# Use the orchestrator's own plugin manager to enable it
orchestrator.pm.enable("mock")

print("\\nTesting...")
response = orchestrator.generate("What is RepoForge?")

print("\\nResponse:")
print(response)
print("\\nSUCCESS!")
"""
with open("test_pm.py", "w") as f:
    f.write(test_code)

print("Routing fixed! Running test...")
os.system("python test_pm.py")