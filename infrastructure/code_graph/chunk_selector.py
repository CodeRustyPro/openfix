"""Chunk selection for code relevance scoring."""
from typing import List, Dict, Tuple
import re
from pathlib import Path


class CodeChunk:
    """Represents a chunk of code with metadata."""
    
    def __init__(self, file_path: str, start_line: int, end_line: int, content: str):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.relevance_score = 0.0
    
    def __repr__(self):
        return f"CodeChunk({self.file_path}:{self.start_line}-{self.end_line}, score={self.relevance_score:.2f})"


class ChunkSelector:
    """Selects relevant code chunks based on issue text."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize chunk selector.
        
        Args:
            chunk_size: Number of lines per chunk
            overlap: Number of lines to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_file(self, file_path: str, content: str) -> List[CodeChunk]:
        """
        Split a file into overlapping chunks.
        
        Args:
            file_path: Path to the file
            content: File content as string
            
        Returns:
            List of CodeChunk objects
        """
        lines = content.split('\n')
        chunks = []
        
        if len(lines) <= self.chunk_size:
            # File is smaller than chunk size, return as single chunk
            return [CodeChunk(file_path, 1, len(lines), content)]
        
        start = 0
        while start < len(lines):
            end = min(start + self.chunk_size, len(lines))
            chunk_content = '\n'.join(lines[start:end])
            chunks.append(CodeChunk(file_path, start + 1, end, chunk_content))
            
            if end >= len(lines):
                break
            
            start = end - self.overlap
        
        return chunks
    
    def extract_keywords(self, issue_text: str) -> List[str]:
        """
        Extract potential keywords from issue text.
        
        Args:
            issue_text: Issue title and body combined
            
        Returns:
            List of keywords
        """
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        # Extract words, convert to lowercase
        words = re.findall(r'\b\w+\b', issue_text.lower())
        
        # Filter out stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Keep unique keywords
        return list(set(keywords))
    
    def score_chunk(self, chunk: CodeChunk, keywords: List[str], file_keywords: Dict[str, float]) -> float:
        """
        Score a chunk's relevance to the issue.
        
        Args:
            chunk: CodeChunk to score
            keywords: List of keywords from issue
            file_keywords: Dict mapping filenames to importance scores
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        score = 0.0
        content_lower = chunk.content.lower()
        
        # Keyword matching in content (40% of score)
        keyword_matches = sum(1 for kw in keywords if kw in content_lower)
        if keywords:
            score += (keyword_matches / len(keywords)) * 0.4
        
        # File path relevance (30% of score)
        file_name = Path(chunk.file_path).name.lower()
        path_parts = Path(chunk.file_path).parts
        
        # Check if any keywords appear in file path
        path_matches = sum(1 for kw in keywords if kw in ' '.join(path_parts).lower())
        if keywords:
            score += (path_matches / len(keywords)) * 0.3
        
        # File type bonus (10% of score)
        if file_name.endswith(('.py', '.js', '.ts', '.tsx', '.jsx')):
            score += 0.1
        
        # Explicit file mentions in issue (20% of score)
        for mentioned_file, mention_score in file_keywords.items():
            if mentioned_file in chunk.file_path:
                score += mention_score * 0.2
                break
        
        return min(score, 1.0)
    
    def select_chunks(self, chunks: List[CodeChunk], issue_text: str, top_k: int = 10, 
                     max_chars_per_chunk: int = 5000) -> List[CodeChunk]:
        """
        Select top K most relevant chunks for an issue.
        
        Args:
            chunks: List of all code chunks
            issue_text: Combined issue title and body
            top_k: Number of chunks to return
            max_chars_per_chunk: Max characters per chunk (for token limits)
            
        Returns:
            List of top K most relevant chunks, sorted by score
        """
        keywords = self.extract_keywords(issue_text)
        
        # Extract file mentions from issue (e.g., "in src/foo.py")
        file_pattern = r'[\w/]+\.\w+'
        mentioned_files = re.findall(file_pattern, issue_text)
        file_keywords = {f: 1.0 for f in mentioned_files}
        
        # Score all chunks
        for chunk in chunks:
            chunk.relevance_score = self.score_chunk(chunk, keywords, file_keywords)
            
            # Truncate if too long
            if len(chunk.content) > max_chars_per_chunk:
                lines = chunk.content.split('\n')
                truncated_lines = lines[:max_chars_per_chunk // 50]  # Rough estimate: 50 chars/line
                chunk.content = '\n'.join(truncated_lines) + f'\n... (truncated from {len(lines)} lines)'
        
        # Sort by score and return top K
        sorted_chunks = sorted(chunks, key=lambda c: c.relevance_score, reverse=True)
        return sorted_chunks[:top_k]
