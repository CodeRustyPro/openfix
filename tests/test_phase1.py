"""Unit tests for Phase 1 components."""
import pytest
from infrastructure.retrieval.chunk_selector import ChunkSelector
from infrastructure.retrieval.embed_adapter import EmbedAdapter

def test_embed_adapter_deterministic():
    adapter = EmbedAdapter()
    vec1 = adapter.embed_texts(["hello"])
    vec2 = adapter.embed_texts(["hello"])
    assert (vec1 == vec2).all()
    
    vec3 = adapter.embed_texts(["world"])
    assert not (vec1 == vec3).all()

def test_chunk_selector_ingest(tmp_path):
    # Create dummy repo
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "test.py").write_text("def foo():\n    pass\n" * 20)
    
    selector = ChunkSelector(str(repo), chunk_size=10, overlap=0)
    selector.ingest()
    
    assert len(selector.chunks) > 0
    assert selector.index is not None
    
    results = selector.query("foo", top_k=1)
    assert len(results) == 1
    assert "test.py" in results[0].file_path
