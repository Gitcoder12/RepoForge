# RepoForge Knowledge Engine (RAG + FastMCP)

RepoForge's local-first retrieval service indexes trusted repository roots into a
SQLite FTS5 store. It exposes read-only retrieval and explicit indexing tools
through the optional standalone FastMCP package.

## Install

```bash
pip install -e ".[rag,dev]"
```

## Configure trusted roots

PowerShell:

```powershell
$env:REPOFORGE_RAG_ROOTS = "C:\work\RepoForge"
$env:REPOFORGE_RAG_DB = "$HOME\.repoforge\rag.sqlite3"
repoforge-rag-mcp
```

Linux/macOS:

```bash
export REPOFORGE_RAG_ROOTS="$HOME/src/RepoForge"
export REPOFORGE_RAG_DB="$HOME/.repoforge/rag.sqlite3"
repoforge-rag-mcp
```

The server uses stdio by default. Add the command and environment variables
to the MCP client configuration. Do not expose an unauthenticated network
listener for a filesystem-reading tool.

## Tools

- `rag_index_directory(directory, collection)`: index text/code files beneath
  an explicitly configured root. Symlinks and common dependency/build folders
  are skipped.
- `rag_search(query, collection, top_k)`: retrieve relevant chunks with path,
  line range, SHA-256 and an untrusted-source marker.
- `rag_list_collections()`: inspect collection counts and roots.

Collections are isolated by name. Keep ARK policy/research material separate
from RepoForge code and repair history.

## Retrieval and safety boundaries

- SQLite FTS5 lexical retrieval is the initial deterministic backend; no
  embedding API, hosted vector database or model key is required.
- Search results are evidence, not instructions. Never execute retrieved text.
- The indexing API is restricted to configured roots and reads files only.
- File-size limits, extension allowlists, symlink rejection and ignored
  dependency/build directories reduce accidental ingestion.
- Retrieval does not enforce authorization within a collection. Do not mix
  documents with different access permissions in one collection.
- This is a local MVP, not a hardened multi-user service. Keep the server on
  stdio for local clients.

## Future adapter

A vector backend (for example Qdrant) can be added behind the same collection
and citation contract after evaluating retrieval quality against a benchmark.
