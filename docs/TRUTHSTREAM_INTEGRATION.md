# TruthStream evidence bridge (RepoForge)

RepoForge can query TruthStream's `/verify` API through `TruthstreamClient` and consume results as external factual context.

```python
from repoforge.truthstream_client import TruthstreamClient

client = TruthstreamClient("https://truthstream.example")
assessments = client.verify("A factual claim that needs corroboration")
for assessment in assessments:
    print(assessment.status, assessment.usable_as_context)
```

The client requires HTTPS (HTTP is allowed only for loopback development), applies timeout and response-size limits, and refuses redirects. The bridge requires a source-backed provenance declaration, HTTPS evidence URLs, stable evidence IDs, retrieval timestamps, and at least two distinct source hosts.

**Distinct hosts do not prove independent ownership or independent reporting.** Provenance completeness does not prove source authenticity or claim truth. Use results as context, never as sole authorization for an engineering action.

TruthStream cannot prove that a repository file changed, a command ran, a dependency is malicious, or an agent violated an engineering rule. Those facts must come from trusted RepoForge adapters and integrity-protected run logs. Never use a claim confidence score alone to sanction an engineering run.

The default TruthStream main-branch retriever is an in-memory demo dataset with missing source URLs and retrieval timestamps. Its output is intentionally rejected.

The client does not authenticate the TruthStream service or sign responses. Production deployment still needs service authentication, replay protection, protected audit logging, and independent validation of source ownership.
