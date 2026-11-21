# Model Lab

Model Lab compares explicitly selected models against the same small, repeatable
set of RepoForge response-contract checks.

## Quick start

```bash
repoforge model-lab --catalog
repoforge providers
repoforge model-lab --target openai:gpt-6.2-sol --target deepseek:deepseek-flash
repoforge model-lab --target openai:gpt-6.2-astra --target ollama:llama3.2 --output model-lab.json
```

Configure each provider first. Remote targets may incur charges and rate limits.
Ollama requires a local service and a model pulled on the machine. Model Lab
never selects a provider automatically, switches providers, or falls back to a
mock. Each target receives up to four sequential requests; execution stops for
that target after its first provider error.

## Suggested starting points

| Role | Target | Why test it |
|---|---|---|
| Frontier reasoning / difficult coding | `openai:gpt-6.2-astra` | High-capability reference |
| Balanced agent / everyday coding | `openai:gpt-6.2-sol` | Quality and latency comparison |
| Claude Sonnet — coding and document workflows | `openrouter:anthropic/claude-sonnet-5.5` | Independent coding and agent comparison |
| Claude Opus — demanding reasoning | `openrouter:anthropic/claude-opus-5.5` | Higher-capability long-horizon comparison |
| Gemini Flash — fast agentic baseline | `openrouter:google/gemini-3.8-flash` | Fast software engineering and agent-task comparison |
| Cost-conscious hosted baseline | `deepseek:deepseek-flash` | Lower-cost hosted comparison |
| Local / privacy-oriented baseline | `ollama:llama3.2` | Local endpoint comparison |

These are starting points, not endorsements or permanent defaults. Model names,
availability and prices can change; use exact IDs supported by your account.
OpenRouter can also route the Claude and Gemini presets above; it uses the exact model ID after `openrouter:`. Check live model availability and routed pricing before use.

## What is measured

The built-in `core` suite checks exact instruction following, permission
denial for an out-of-scope destructive tool request, treatment of quoted
prompt-injection text as untrusted data, and a bounded change-plan contract.
The report contains per-case pass/fail status, request latency and aggregate
pass rate. It does not estimate token cost because the current provider
interface does not expose consistent usage metadata.

## Limits

- This is a smoke-evaluation suite, not a general ranking of model intelligence.
- The rubric checks exact strings or required JSON fields; it does not prove
  semantic correctness, robust prompt-injection resistance, alignment, or safe
  tool execution.
- It does not run agents with real tools or execute generated code.
- Compare models on representative, held-out tasks before production selection.
- Compare only when model versions, provider settings and evaluation conditions
  are recorded.
- No model is automatically selected as the winner.

For serious evaluation, use versioned task sets, blinded comparisons, multiple
runs, domain experts, calibrated graders and separate adversarial evaluations.
Do not describe this starter suite as a safety certification.


## Provider references

Verify current model IDs and endpoint behavior against the provider's official
documentation before refreshing this catalogue:

- OpenAI model catalogue: https://developers.openai.com/api/docs/models
- OpenAI GPT-6.2 API migration notes: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.2-astra
- DeepSeek model and pricing list: https://api-docs.deepseek.com/quick_start/pricing/
- DeepSeek model discovery endpoint: https://api-docs.deepseek.com/api/list-models/
