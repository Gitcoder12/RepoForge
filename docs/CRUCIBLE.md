# RepoForge Crucible

Crucible is a lightweight heuristic wrapper around a model provider. It is a defense-in-depth signal filter, **not** a security boundary, prompt-injection solution, sandbox, or proof that generated content is safe.

## Current behavior

- Applies known-pattern secret redaction to both the user prompt and system prompt before forwarding them to the wrapped provider.
- Checks complete generated text against a small set of known destructive-command patterns.
- Buffers streamed output before exposing any chunks, so a pattern split across chunk boundaries is still inspected as a single response.
- Rejects streamed responses larger than 1 MB rather than releasing uninspected content.

## Important limitations

- Secret patterns cover only a limited set of common token formats. They do not detect every credential, private key, personal datum, connection string, or secret encoded in another format.
- Dangerous-output patterns are deliberately narrow. They can miss obfuscated commands, platform-specific operations, scripts, malicious code, or harmful instructions expressed in other ways.
- Pattern matches can produce false positives. A text snippet mentioning a command is not necessarily an executable action.
- Buffering prevents chunk-boundary bypasses for the current pattern set, but it does not make the stream safe or prevent other provider-side behavior.
- Crucible does not control tools, filesystem access, network permissions, process execution, model weights, or the environment in which a downstream agent runs.

## Recommended use

Keep Crucible as one supplementary check. For any system that executes code or takes actions, enforce permissions outside the model, use an isolated runtime, remove host credentials, restrict network egress, impose resource limits, log decisions, and require approval for consequential operations. Never rely on Crucible as the only safety control.
