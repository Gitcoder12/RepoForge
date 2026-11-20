# RepoForge Sentinel — Read-only threat-signal MVP

Sentinel is the first repository-intelligence security subsystem. It scans selected source/configuration files for review signals without importing, executing, installing, or modifying repository content.

## Run

```bash
python -m repoforge.sentinel /path/to/repository
```

The command emits JSON with rule IDs, severity, file/line locations, bounded evidence, explanations and remediation suggestions.

## Initial rules

- Dynamic evaluation via `eval` / `exec`
- Shell-enabled subprocess calls
- `os.system` command execution
- Pickle deserialization
- Potentially unsafe YAML loading

## Safety and interpretation

- Read-only; no repository code is executed.
- Skips common generated/vendor directories, symlinks and files over 1 MB.
- Uses bounded file traversal and evidence snippets.
- Findings are heuristics, not proof of malicious intent, exploitability or vulnerability.
- Absence of findings is not a clean security certification.
- It does not yet scan secrets, dependencies, CI workflows, licenses or runtime behaviour.

A repository can be legitimate and still contain dangerous capabilities. Sentinel reports capability-related review leads; it does not label repository owners as malicious or automatically blacklist research.

## Next milestones

1. Add dependency and lockfile risk inventory with source attribution.
2. Add CI/workflow permission and secret-exposure checks.
3. Add SARIF output and suppressions with reviewer rationale.
4. Add a consent-based difficult-repository catalogue with license/visibility metadata.
5. Add isolated dynamic analysis only after a separately reviewed sandbox exists.
6. Add RAG-backed findings with exact source references; retrieved text remains untrusted.
7. Add MCP integrations behind explicit tool permissions and human approval.
