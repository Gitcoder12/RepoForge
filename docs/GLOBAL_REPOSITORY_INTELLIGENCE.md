# Global Repository Intelligence & Ranking Engine

## Product goal

Build a GitHub-wide discovery and ranking system that distinguishes popularity, engineering quality, performance, activity, innovation signals, reliability, and ecosystem criticality. Never present a single popularity metric as overall quality.

## Ranking collections

- Best engineered: transparent composite of test signals, CI health where observable, maintainability proxies, documentation, security posture, release discipline, and issue/PR responsiveness.
- Largest: GitHub-reported repository size plus measured file count, language breakdown, and source/generated/vendor separation when safely available.
- Fastest: only comparable benchmark results with workload, hardware, runtime, version, methodology, and reproducible artifacts. Never infer speed from stars or repository metadata.
- Trending: star/fork growth over defined time windows, recent commits, releases, and contributor growth; distinguish growth from absolute popularity.
- Most critical: dependency graph reach, reverse dependencies, ecosystem centrality, infrastructure role, and concentration risk.
- Most innovative: emerging topics, novel releases, research artifacts, and adoption signals; label as a heuristic, not objective truth.
- Most reliable: release stability, maintenance continuity, security response, tests, CI evidence, and incident history where public.

## Data sources

Primary discovery: GitHub REST/GraphQL repository search and metadata, dependency graph/dependents where available, repository manifests/lockfiles, releases, commits, contributors, issues, pull requests, advisories, and Actions status where accessible.

Use public GitHub APIs with authenticated access when available. Respect rate limits, pagination, API terms, privacy, and repository visibility. Cache responses with source timestamps and refresh policies. Do not scrape private content or bypass access controls.

## Ranking methodology

Each category has its own score, published formula, component weights, data coverage, freshness timestamp, and confidence. Show raw metrics alongside normalized scores. Missing data must be marked unknown, not treated as zero or silently imputed. Exclude archived repositories only when the category's definition requires it; disclose exclusions.

Popularity must not dominate engineering quality. Performance ranking requires apples-to-apples benchmark evidence. Criticality should separate direct dependents from transitive reach and identify incomplete ecosystem coverage.

## Product interface

- Global overview with category leaderboards and filters (language, topic, license, owner, activity, size).
- Repository profile with score breakdown, provenance, dependencies/dependents, trends, benchmark evidence, security and maintenance signals.
- Compare view for multiple repositories.
- Watchlist and change history.
- Exportable JSON/CSV reports.
- Evidence links for every metric and score component.

## Reliability and abuse resistance

Detect forks, mirrors, bot-driven activity, artificial star/fork spikes, duplicate repositories, archived projects, and low-coverage data. Never label a repository "secure" or "best" solely from public metadata. Explain uncertainty and allow users to inspect raw evidence.

## Architecture

Discovery adapters -> normalized repository records -> time-series metric store -> dependency graph -> category scoring engines -> evidence/provenance layer -> API/UI.

Keep collectors, scoring formulas, and UI decoupled. Add provider interfaces so non-GitHub ecosystems can be added later without changing ranking semantics.

## Initial MVP

1. GitHub public repository search and metadata ingestion.
2. Leaderboards: stars/popularity, size, recent activity, trending (using stored snapshots), and quality-signal coverage.
3. Repository detail and compare pages with transparent metric breakdown.
4. Dependency criticality prototype using available dependency manifests and GitHub dependent signals, with explicit coverage limitations.
5. Benchmark registry for verified performance results only.
6. Rate-limit-aware caching, pagination, provenance, and data freshness.

## Acceptance criteria

- Every score is explainable and reproducible from stored evidence.
- Category definitions and formulas are versioned.
- No unsupported "fastest" or "best" claims.
- API rate limits and partial data are visible.
- Search and rankings deduplicate forks and mirrors where possible.
- User can drill from rank to source evidence.
- Rankings can be recalculated when formulas change.