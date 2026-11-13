import sys
sys.path.insert(0, 'src')
from repoforge.providers.ollama import OllamaProvider

print("⏳ Calling local Ollama (llama3)...")
provider = OllamaProvider(model="llama3")

response = provider.generate(
    prompt="What is RepoForge in one sentence?",
    system_prompt="You are a helpful AI assistant."
)

print("\n✅ AI Response:")
print("-" * 60)
print(response)
print("-" * 60)
