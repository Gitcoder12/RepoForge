# Extreme Testing Lab

## Purpose

Extreme Testing Lab measures RepoForge's practical capacity on difficult external repositories: how accurately it inventories, understands, ranks, plans for, tests, and safely reports on repositories beyond ordinary demo scale.

This complements the existing difficulty engine and TestForge. It must not silently execute repository-controlled code.

## Modes

1. **Inspect (default):** inventory files, languages, sizes, manifests, dependency metadata, test configuration, documentation, and repository topology. No project code execution.
2. **Plan:** produce a proposed test/analysis plan and resource estimate. No execution.
3. **Sandboxed test (explicit opt-in):** execute selected tests only in a disposable OS/container sandbox with no credentials, no host mounts, network disabled by default, resource quotas, bounded logs, and a hard timeout. If a real sandbox is unavailable, refuse execution and remain in inspect/plan mode.

## Difficulty profiles

- **Hard:** medium/large multi-module repository with normal build/test tooling.
- **Extreme:** monorepo, multiple languages/build systems, large dependency graph, generated/vendor content, extensive tests, and incomplete documentation.
- **Adversarial:** malformed manifests, hostile README/issue text, prompt injection in repository files, path traversal fixtures, oversized files, symlink edge cases, dependency ambiguity, and resource-exhaustion fixtures.

Profiles are determined by measurable repository features and explicit thresholds, never by repository branding alone.

## Test dimensions

- inventory completeness and scan time
- language/build/test framework detection accuracy
- dependency graph coverage and unresolved edges
- repository structure and module-boundary understanding
- quality/difficulty score calibration against a labelled corpus
- test discovery precision and recall
- test execution reliability in the sandbox (when enabled)
- plan usefulness and actionability, scored against a rubric
- path safety, secret leakage, network isolation, and sandbox escape attempts
- CPU, memory, disk, process, wall-time, and output-budget behaviour

## Workflow

1. Pin a repository URL and commit SHA; record provenance and license metadata.
2. Run metadata-only inspection.
3. Classify difficulty from measurable signals and show the reasons.
4. Generate a resource-bounded test plan.
5. Require explicit approval for sandboxed execution.
6. Execute only allowlisted commands in an isolated disposable workspace.
7. Capture bounded logs, exit codes, timings, resource usage, and artifacts.
8. Compare results to a baseline and produce a report.
9. Destroy the workspace; never modify the source repository.

## Safety requirements

- Never run untrusted repository tests on the host.
- Never pass a command through a shell; use validated argument arrays.
- No secrets, credentials, SSH agent, host mounts, or cloud metadata access.
- Network disabled by default; explicit allowlists only.
- Bound CPU, memory, disk, process count, output bytes, and wall time.
- Reject path traversal and unsafe symlink escapes.
- Do not apply fixes to the target repository during a stress test.
- If sandbox guarantees cannot be verified, disable execution and report why.

## Capacity report

Produce JSON and Markdown containing: schema_version, run_id, repository URL, pinned commit SHA, profile and classification evidence, scanner coverage, language/build/test detection, dependency graph metrics, planned/actual commands, per-command exit status and duration, resource usage, safety events, errors, skipped checks, baseline comparison, artifact hashes, and timestamps.

Use a vector of measurements rather than one vanity score. If a composite score is displayed, publish its formula, weights, missing-data handling, and confidence.

## Acceptance criteria

- Inspect mode is safe for untrusted repositories and performs no code execution.
- Test mode is unavailable unless a verifiable OS-level sandbox is present.
- Classification is explainable and reproducible.
- All limits and skipped checks appear in the report.
- A failed scan or timeout is a valid recorded outcome, not silently discarded.
- Stress testing never changes the source repository.

## Current implementation status

This document defines the module specification. It does not claim that the runner, sandbox, or full scoring pipeline is implemented.