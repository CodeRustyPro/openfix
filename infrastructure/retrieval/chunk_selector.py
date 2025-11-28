"""Chunk selector using FAISS and embeddings."""
import os
import logging
from typing import List, Dict, Any
import numpy as np
from dataclasses import dataclass

try:
    import faiss
except ImportError:
    faiss = None

from infrastructure.retrieval.embed_adapter import EmbedAdapter

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    file_path: str
    start_line: int
    end_line: int
    content: str
    metadata: Dict[str, Any]

class ChunkSelector:
    def __init__(self, repo_path: str, chunk_size: int = 100, overlap: int = 10):
        self.repo_path = repo_path
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[Chunk] = []
        self.index = None
        self.embed_adapter = EmbedAdapter()

    def ingest(self):
        """Scan repo and chunk files."""
        self.chunks = []
        exclude_dirs = {'.git', '.yarn', 'node_modules', 'dist', 'build', '.venv', '__pycache__', 'vendor'}
        
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith(('.lock', '.png', '.jpg', '.pyc', '.min.js')):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self._chunk_file(file_path, content)
                except UnicodeDecodeError:
                    continue # Skip binary
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")

        self._build_index()

    def _chunk_file(self, file_path: str, content: str):
        lines = content.splitlines()
        if not lines:
            return
            
        rel_path = os.path.relpath(file_path, self.repo_path)
        
        for i in range(0, len(lines), self.chunk_size - self.overlap):
            chunk_lines = lines[i:i + self.chunk_size]
            chunk_content = '\n'.join(chunk_lines)
            self.chunks.append(Chunk(
                file_path=rel_path,
                start_line=i + 1,
                end_line=i + len(chunk_lines),
                content=chunk_content,
                metadata={"len": len(chunk_content)}
            ))

    def _build_index(self):
        if not self.chunks:
            return

        texts = [c.content for c in self.chunks]
        embeddings = self.embed_adapter.embed_texts(texts)
        
        dim = embeddings.shape[1]
        
        if faiss:
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(embeddings)
        else:
            # Simple fallback if FAISS missing
            self.index = embeddings # Store raw vectors

    def query(self, query_text: str, top_k: int = 5) -> List[Chunk]:
        if not self.chunks:
            return []

        query_vec = self.embed_adapter.embed_texts([query_text])[0]
        
        if faiss and isinstance(self.index, faiss.IndexFlatL2):
            D, I = self.index.search(np.array([query_vec]), top_k)
            indices = I[0]
        else:
            # Numpy cosine similarity fallback
            scores = np.dot(self.index, query_vec)
            indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in indices:
            if idx < len(self.chunks) and idx >= 0:
                results.append(self.chunks[idx])
        
        return results
