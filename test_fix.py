# test_fix.py - offline / env-based smoke test
# Never hardcode real API keys. Use .env or mock.
import os
from dotenv import load_dotenv

load_dotenv()

# Prefer env; fall back to mock-style check
API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("REPOFORGE_TEST_MODEL", "deepseek-chat")

if not API_KEY:
    print("No API key in env — skipping live test. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.")
else:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'Hello, RepoForge is working!'"}],
        )
        print("SUCCESS:", response.choices[0].message.content)
    except Exception as e:
        print("FAILED:", e)
