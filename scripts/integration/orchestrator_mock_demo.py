import sys
sys.path.insert(0, 'src')

from repoforge.orchestrator import AIOrchestrator
from repoforge.providers.mock import MockProvider

print("Setting up...")
orchestrator = AIOrchestrator()
orchestrator.register("mock", MockProvider())

# Use the orchestrator's own plugin manager to enable it
orchestrator.pm.enable("mock")

print("\nTesting...")
response = orchestrator.generate("What is RepoForge?")

print("\nResponse:")
print(response)
print("\nSUCCESS!")
