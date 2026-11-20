# TruthStream evidence bridge (RepoForge)

RepoForge can consume TruthStream results as external factual context, but only when every cited item has a stable evidence ID, HTTPS source URL and retrieval timestamp, TruthStream declares `source_backed`, and at least two distinct source hosts are represented.

TruthStream does not prove that a repository file changed, a command ran, a dependency is malicious, or an agent violated an engineering rule. Those facts must be collected from trusted RepoForge adapters and integrity-protected run logs. Never use a claim confidence score alone to sanction an engineering run.

The default TruthStream main-branch retriever is an in-memory demo dataset with missing source URLs and retrieval timestamps. Its output is intentionally rejected. The bridge is a pure parser, not an HTTP client or source-truth oracle. Production integration still requires authenticated service identity, TLS, response limits, replay protection, and audit logging.
