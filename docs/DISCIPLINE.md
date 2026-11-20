# RepoForge Discipline & Enforcement

RepoForge discipline is scoped to a single engineering run. It governs the permissions an adapter should grant to that run; it does not change model weights or infer intent.

## Enforcement ladder

- `CLEAR`: normal approved workflow.
- `NOTICE`: record a low-severity issue.
- `READ_ONLY`: stop repository writes; permit inspection and planning.
- `ISOLATED_REVIEW`: require owner review; do not run target tests or install dependencies.
- `HALTED`: owner-stopped run; create a new run after review.

Repeated validation failures remove write capability so the agent must stop repeating a failing patch strategy and return to planning. Severe destructive Git, protected-path, or unapproved-write events require isolated review. Low-confidence findings and drift-only signals request review but do not independently trigger sanctions.

## Integration contract

Call `RunDiscipline.record(RunEvidence(...))` for trusted, structured events and apply the returned `RunPolicy` at every write, test, and dependency-install boundary. Evidence must be produced by trusted adapters, not by the model being governed. Bind every event to the current run ID. A new run starts with fresh state.

## Limitations

This is a deterministic policy primitive, not an OS sandbox or Git transaction manager. It does not authenticate the owner, roll back files, protect the main branch, kill processes, revoke credentials, detect drift, or persist an immutable audit. The caller must enforce `writable`, `may_run_tests`, and `may_install_dependencies`; the booleans do nothing unless every relevant adapter checks them. Scanner heuristics are signals, not proof of maliciousness.

Run tests with `pytest tests/test_discipline.py`.
