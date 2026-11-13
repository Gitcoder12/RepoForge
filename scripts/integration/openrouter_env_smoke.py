import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, 'src')
from repoforge.providers.openrouter import OpenRouterProvider

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key or api_key == "your_openrouter_key_here":
    print("❌ Error: Please add your OPENROUTER_API_KEY to the .env file")
    print("   -> Get a free key at: https://openrouter.ai/keys")
else:
    print("⏳ Calling OpenRouter (Free Model)...")
    # Using a explicitly free model on OpenRouter
    provider = OpenRouterProvider(api_key=api_key, model="meta-llama/llama-3-8b-instruct:free")
    
    response = provider.generate(
        prompt="What is RepoForge in one sentence?",
        system_prompt="You are a helpful AI assistant."
    )
    
    print("\n✅ AI Response:")
    print("-" * 60)
    print(response)
    print("-" * 60)
