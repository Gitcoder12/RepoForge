# RepoForge Blacksmith & Megazords

## Blacksmith

Blacksmith inspects a local repository without executing its code, computes a transparent RepoRank, and proposes bounded repairs.

```bash
# Inspect and preview a repair plan (default; no files changed)
repoforge blacksmith /path/to/repository

# Apply only safe create-if-absent repairs
repoforge blacksmith /path/to/repository --apply
```

The first repair adapter can create a conservative `.gitignore` if one is missing. It never overwrites an existing file, deletes files, installs dependencies, invokes an LLM, or runs the target repository's tests. Missing CI and test coverage are reported as review-required work because project-specific commands and assertions must be correct—not fabricated.

RepoRank is a deterministic repository-hygiene score out of 100. Its dimensions are documentation (15), tests (20), CI (20), project configuration (15), licensing (10), ignore rules (5), security process (10), and quality tooling (5). This is not a code-quality benchmark, security certification, or ranking against other repositories. It measures the presence of inspectable engineering signals only.

The scan is bounded to 20,000 files by default, skips common generated/dependency directories, and does not follow symbolic links. The before/after report recalculates the same score after applied changes.

## UpgradeForge — selectable repository improvement paths

Blacksmith remains the evidence-gathering and hygiene-ranking layer. UpgradeForge consumes its snapshot and offers a ranked catalogue of concrete improvement options. Owners can choose a profile or exact option IDs; the command produces a review plan and does not silently modify the target.

```bash
# All currently applicable options
repoforge upgrade /path/to/repository

# Focused programmes
repoforge upgrade /path/to/repository --profile foundation
repoforge upgrade /path/to/repository --profile security
repoforge upgrade /path/to/repository --profile quality
repoforge upgrade /path/to/repository --profile delivery
repoforge upgrade /path/to/repository --profile maintainability

# Select exact options
repoforge upgrade /path/to/repository --select tests-real,ci-pipeline
```

Each option reports its evidence, impact, effort, risk, implementation guidance, verification criteria and priority score. The current catalogue covers README/documentation, real tests, CI, project manifests, license selection, ignore rules, security maintenance and quality tooling.

The `rank_points_available` value represents the hygiene points attached to missing signals in the current scoring model. It is not a predicted quality gain, and it does not mean an upgrade has been applied. RepoRank is a transparent engineering-hygiene indicator, not a benchmark of correctness, performance, security or product value.

### Safety contract

- Recommendation-only by default; no target repository code is executed.
- No placeholder tests are generated to manufacture green results.
- No license is chosen automatically; the owner must decide.
- No existing file is overwritten and no file is deleted.
- Project-specific CI, security and test changes require maintainer review and verification.
- The existing `.gitignore` create-only repair is still a separate safe-repair action.

### Current implementation boundary

UpgradeForge currently generates and filters a ranked recommendation catalogue. It does not yet implement the recommended test suites, CI workflows, security policies or language-specific refactors. Those require separate approved implementation adapters, validation and rollback. Do not present recommendations as completed upgrades.
## Megazords

Megazords compares two to thirty local repository paths and ranks combinations by inferred capability complementarity and shared languages.

```bash
repoforge megazords /workspace/ARK /workspace/RepoForge /workspace/Overdrive
```

Its report includes a fit score, complementary capabilities, candidate architecture pattern, and risks to resolve. It is recommendation-only: it does not merge repositories, copy source files, install dependencies, or claim that a pairing is already compatible.

Capability detection is heuristic and uses repository names, README text, manifests and file structure. Treat each suggestion as an engineering hypothesis. Confirm package versions, API contracts, data models, licensing and operational ownership before integrating systems.

## Current limits

- Blacksmith's automatic repair surface is deliberately narrow: create a missing generic `.gitignore`.
- Language-specific code repair adapters (Ruff, ESLint/Prettier, gofmt, rustfmt), patch validation and rollback are future work.
- Blacksmith does not currently diagnose or repair arbitrary semantic bugs across all languages.
- RepoRank is a hygiene score, not a measure of runtime speed, correctness or product quality.
- Megazords does not inspect private remote APIs or modify repositories.
