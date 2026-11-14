from repoforge.providers.openrouter import OpenRouterProvider

provider = OpenRouterProvider()

response = provider.generate(
    "Reply with exactly: RepoForge OpenRouter is working!"
)

print(response)