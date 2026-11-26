# RepoForge Ecosystem Capability Adapters

Status: architecture proposal; integrations below are not yet implemented.

## Purpose
RepoForge should orchestrate bounded analyzers rather than reimplement every parser, vulnerability database, test runner and static-analysis engine.

## Internal capability candidates

| Source | Capability | RepoForge use |
|---|---|---|
| Langfix | Language detection and optional validation | Select language-aware analyzers |
| Chaos-Control | Streaming normalization, deduplication, provenance | Prepare scan inventories and large result streams |
| Onto-Sieve | Strict record validation and quarantine | Validate plugin and report payloads |
| Hardware-Box | Schema validation and audit patterns | Reuse validation design, not hardware domain logic |
| CyberRadar | CVE/KEV/EPSS enrichment | Dependency and component risk evidence |
| AttackWatch | Event/rule detection | Analyze security events from test runs |
| Truthstream | Evidence-based explanation | Explain findings while retaining sources |
| Commander | Suggestion ranking/deduplication | Rank remediation candidates, never execute them |

## External projects to evaluate
- Tree-sitter: syntax trees and incremental parsing through Langfix.
- Semgrep: multi-language static analysis; ingest SARIF/JSON findings as evidence.
- OSV-Scanner: dependency vulnerability scanning.
- OWASP dep-scan: compare SBOM, reachability and dependency risk coverage; avoid redundant scans.
- Hypothesis: property-based tests for ranking, parsers and policy engines.
- Atheris: fuzz parsers, archive readers, manifests and action boundaries.
- NetworkX: graph prototyping; use measured lightweight adjacency-list algorithms in hot paths.

Candidates only. Verify licenses, maintenance, supported ecosystems, pinning, data handling and transitive dependencies before adoption.

## Analyzer adapter contract
Declare adapter ID/version, supported languages, input/output schemas, target-code execution (default no), network requirements (default disabled), timeout/memory/output limits, exit-code semantics and provenance.

Normalize results into findings with repository revision, path, line range, rule ID, severity, evidence, tool/version and scan time. Preserve raw output for debugging subject to secret redaction.

## Complexity strategy

| Workload | Preferred approach | Complexity |
|---|---|---|
| File inventory | Iterative traversal + precompiled ignore rules | O(F+B), F files and B bytes inspected |
| Changed-file rescans | Content digest cache keyed by path, digest and analyzer version | O(changed bytes) after initial scan |
| Top-k ranking | Bounded heap when k << N | O(N log k), O(k) extra memory |
| Full ranking | One deterministic sort | O(N log N) |
| Dependency graph | Adjacency lists | O(V+E) construction |
| Cycle detection | Tarjan/Kosaraju SCC | O(V+E) |
| Exact duplicate detection | Hash fingerprints, verify collision candidates | Expected O(total bytes) |
| Large reports | Incremental aggregation/bounded batches | O(batch size) working memory |
| Repeated set overlap | Bitsets only for stable, dense universes | Benchmark against hash sets |

Do not use top-k if the full ordered ranking is required. Do not use bitsets for sparse, huge identifier spaces without measuring memory.

## Security boundary
- Never execute arbitrary repository tests/build scripts/hooks on the host.
- TestForge needs OS-level sandbox/container/VM isolation with CPU, memory, process, filesystem and network limits before untrusted code can be treated as safely executable.
- Network disabled by default; allowlist explicit requirements.
- Repository files, comments and analyzer output are untrusted data, never instructions.
- Recheck canonical paths and symlinks at the final write boundary; document TOCTOU limitations.
- Separate planning, authorization and execution. Require human approval and recoverable Git checkpoints.

## Measurement gate
Record baseline/candidate commit, corpus shape, wall time, peak RSS, hardware/runtime, cold/warm cache, output equivalence and test results. Use 1K, 10K, 100K and 1M fixtures where realistic. No speedup claims without workload and environment.

## Delivery
1. Add versioned analyzer finding envelope and adapter registry.
2. Add optional Semgrep and OSV-Scanner adapters with contract tests.
3. Add Tree-sitter via Langfix.
4. Add Hypothesis properties and Atheris fuzz targets.
5. Fix TestForge isolation before untrusted execution.
6. Add incremental caching and top-k only where profiling proves a bottleneck.