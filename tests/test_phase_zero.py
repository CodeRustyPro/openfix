"""Simple test suite for Phase Zero components."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.code_graph.chunk_selector import ChunkSelector, CodeChunk


class TestChunkSelector:
    """Test chunk selection logic."""
    
    def test_keyword_extraction(self):
        selector = ChunkSelector()
        keywords = selector.extract_keywords("Fix the dealer logic in bananajack game")
        assert "fix" in keywords
        assert "dealer" in keywords
        assert "logic" in keywords
        assert "bananajack" in keywords
        assert "the" not in keywords  # stop word
    
    def test_chunk_scoring(self):
        selector = ChunkSelector()
        chunk = CodeChunk("src/game.py", 1, 100, "def dealer_logic():\n    pass")
        score = selector.score_chunk(chunk, ["dealer", "logic"], {})
        assert score > 0
        assert score <= 1.0
    
    def test_select_top_chunks(self):
        selector = ChunkSelector()
        chunks = [
            CodeChunk("src/dealer.py", 1, 10, "dealer code"),
            CodeChunk("src/player.py", 1, 10, "player code"),
            CodeChunk("src/game.py", 1, 10, "game logic dealer"),
        ]
        
        selected = selector.select_chunks(chunks, "fix dealer bug", top_k=2)
        assert len(selected) == 2
        assert all(c.relevance_score > 0 for c in selected)


class TestIngestion:
    """Test code ingestion."""
    
    def test_file_filtering(self):
        from infrastructure.code_graph.ingestion import Ingestor
        ingestor = Ingestor()
        
        assert ingestor._is_text_file("src/code.py")
        assert ingestor._is_text_file("src/code.ts")
        assert not ingestor._is_text_file("LICENSE")
        assert not ingestor._is_text_file("yarn.lock")
        assert not ingestor._is_text_file("file.min.js")


def test_confidence_scoring():
    """Test confidence score calculation."""
    from infrastructure.validation.report_confidence import compute_confidence
    
    # All tests pass, no linter issues
    score = compute_confidence(tests_passed=5, tests_failed=0, linter_issues=0)
    assert score >= 90
    
    # Some failures
    score = compute_confidence(tests_passed=3, tests_failed=2, linter_issues=5)
    assert 40 <= score <= 75
    
    # All fail
    score = compute_confidence(tests_passed=0, tests_failed=5, linter_issues=20)
    assert score < 40


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
