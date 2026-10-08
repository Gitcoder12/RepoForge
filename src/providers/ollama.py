import requests
import json
import sys
import os

print("=" * 60)
print("OLLAMA MODEL DOWNLOADER")
print("=" * 60)

# 1. Check if Ollama is running
try:
    requests.get("http://localhost:11434/api/tags", timeout=2)
except requests.exceptions.ConnectionError:
    print("❌ Ollama is not running.")
    print("   -> Open a new terminal and run: ollama serve")
    sys.exit(1)

# 2. Download the model automatically
print("⏳ Downloading 'llama3' model (this may take a minute)...")
try:
    response = requests.post("http://localhost:11434/api/pull", json={"name": "llama3"}, stream=True)
    for line in response.iter_lines():
        if line:
            status = json.loads(line).get("status", "")
            print(f"   -> {status}")
except Exception as e:
    print(f"❌ Failed: {e}")