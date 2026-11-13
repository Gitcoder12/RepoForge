# RepoForge — Feature Upgrade Plan

**Snapshot:** 2026-11-13

## Product/research objective

A tool intended to inspect software repositories, identify engineering issues, plan improvements and safely validate proposed changes.

## P0 — correctness, scope and evidence

- [ ] Choose one canonical installable package and fix all console-script/module entry points together.
- [ ] Make editable install, package import, CLI help and clean-environment test suite pass in CI.

## P1 — complete workflow

- [ ] Implement an explicit read-only analysis mode and a reviewed patch proposal workflow.
- [ ] Require human approval, diff preview, path allowlists and rollback checkpoints before any write operation.

## P2 — differentiation and scale

- [ ] Add benchmark repositories and measure defect detection precision/recall.
- [ ] Support independent analyzer plugins with permissions and audit records.

## Contribution-sized work packages

1. Reproduce one defect or establish one measurable research question.
2. Implement one bounded fix or experiment with focused tests.
3. Publish commands, environment, inputs, outputs and failure modes.
4. Add a reviewer-readable explanation and update ACTIVITY_LOG.md.

## Definition of done

- [ ] Clean setup succeeds from documented instructions.
- [ ] Tests/evaluations include happy path, boundary cases and failures.
- [ ] Results are reproducible and claims match the measured evidence.
- [ ] A human reviewer can inspect the diff and approve the scope.
