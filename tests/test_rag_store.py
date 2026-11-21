"""Tests for the local RepoForge RAG store."""

import pytest

from repoforge.rag.store import LocalKnowledgeBase, RetrievalError


def make_store(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    db = tmp_path / "knowledge.sqlite3"
    return root, LocalKnowledgeBase(db, allowed_roots=[root], chunk_lines=4, overlap_lines=1)


def test_index_and_search_return_citations_and_hashes(tmp_path):
    root, store = make_store(tmp_path)
    (root / "safety.md").write_text(
        "# Safety\n\nNever execute untrusted repository code without isolation.\n",
        encoding="utf-8",
    )
    result = store.index_directory(root, "policies")
    hits = store.search("execute untrusted code isolation", "policies")
    assert result["files_indexed"] == 1
    assert hits
    assert hits[0]["source"] == "safety.md"
    assert hits[0]["citation"].startswith("safety.md:")
    assert len(hits[0]["sha256"]) == 64
    assert hits[0]["trust"] == "untrusted_source_material"


def test_collections_are_isolated(tmp_path):
    root, store = make_store(tmp_path)
    (root / "ark.md").write_text("ARK threat monitor policy.", encoding="utf-8")
    store.index_directory(root, "ark")
    assert store.search("threat monitor", "ark")
    assert store.search("threat monitor", "repoforge") == []


def test_indexing_outside_allowed_roots_is_rejected(tmp_path):
    root, store = make_store(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(RetrievalError, match="outside configured"):
        store.index_directory(outside, "test")


def test_invalid_collection_and_top_k_are_rejected(tmp_path):
    root, store = make_store(tmp_path)
    with pytest.raises(RetrievalError):
        store.index_directory(root, "../escape")
    with pytest.raises(RetrievalError):
        store.search("query", "default", 21)


def test_ignored_directories_and_symlinks_are_not_indexed(tmp_path):
    root, store = make_store(tmp_path)
    ignored = root / ".git"
    ignored.mkdir()
    (ignored / "secret.md").write_text("hidden token", encoding="utf-8")
    target = root / "target.md"
    target.write_text("safe target", encoding="utf-8")
    link = root / "linked.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")
    store.index_directory(root, "test")
    assert store.search("hidden token", "test") == []
    assert store.search("safe target", "test")


def test_collection_reindex_replaces_old_content(tmp_path):
    root, store = make_store(tmp_path)
    doc = root / "notes.md"
    doc.write_text("oldalpha retrieval phrase", encoding="utf-8")
    store.index_directory(root, "notes")
    doc.write_text("newbeta retrieval phrase", encoding="utf-8")
    store.index_directory(root, "notes")
    assert store.search("oldalpha", "notes") == []
    assert store.search("newbeta", "notes")
