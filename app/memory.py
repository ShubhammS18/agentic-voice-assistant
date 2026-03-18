from dataclasses import dataclass

@dataclass
class MemoryEntry:
    turn_id: str
    transcript: str
    response: str
    agent_used: str
    timestamp: float

class SemanticMemory:
    def retrieve(self, query: str) -> list:
        return []  

    def store(self, entry: MemoryEntry):
        pass

semantic_memory = SemanticMemory()