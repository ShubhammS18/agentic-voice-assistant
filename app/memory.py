# app/memory.py
import faiss
import numpy as np
import time
from dataclasses import dataclass

_MODEL = None

def get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return _MODEL


@dataclass
class MemoryEntry:
    turn_id: str
    transcript: str
    response: str
    agent_used: str
    timestamp: float


class SemanticMemory:
    """FAISS-backed semantic memory over past conversation turns."""

    def __init__(self, dim: int = 384, top_k: int = 2):
        self.index = faiss.IndexFlatIP(dim)
        self.entries: list[MemoryEntry] = []
        self.top_k = top_k

    def store(self, entry: MemoryEntry):
        model = get_model()
        text = f"{entry.transcript} {entry.response}"
        embedding = model.encode([text], normalize_embeddings=True)
        self.index.add(embedding)
        self.entries.append(entry)
        print(f'[memory] stored turn {entry.turn_id} — total: {len(self.entries)}')

    def retrieve(self, query: str) -> list[MemoryEntry]:
        if not self.entries:
            return []
        model = get_model()
        q_emb = model.encode([query], normalize_embeddings=True)
        k = min(self.top_k, len(self.entries))
        scores, indices = self.index.search(q_emb, k)
        results = [self.entries[i] for i in indices[0] if i < len(self.entries)]
        if results:
            print(f'[memory] retrieved {len(results)} past turns for: "{query[:50]}"')
        return results


semantic_memory = SemanticMemory()