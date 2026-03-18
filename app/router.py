import time
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer('all-MiniLM-L6-v2')

DOMAIN_DESCRIPTIONS = {
    'rag': (
        'questions about documents, policies, laws, regulations, visa rules, '
        'immigration policy, company procedures, technical guides, '
        'knowledge base content, internal documentation, how-to guides'),
    'web': (
        'current events, recent news, live prices, weather, today, '
        'latest updates, real-time information, things happening now, '
        'recent announcements, breaking news'),
    'data': (
        'specific facts, system specs, configuration values, tech stack, '
        'supported languages, latency numbers, version information, '
        'key-value lookups, structured data fields')}

# Pre-compute at import time — reused on every request, zero API cost
DOMAIN_EMBEDDINGS = {domain: MODEL.encode([desc], normalize_embeddings=True)[0]
                    for domain, desc in DOMAIN_DESCRIPTIONS.items()}

def route_query(sub_queries: list[str]) -> tuple[str, int]:
    """Returns (winning_domain, route_ms). No API call — pure local vector math."""
    t_start = time.perf_counter()
    query_embeddings = MODEL.encode(sub_queries, normalize_embeddings=True)
    avg_embedding = np.mean(query_embeddings, axis=0)
    avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
    
    scores = {domain: float(np.dot(avg_embedding, domain_emb))
            for domain, domain_emb in DOMAIN_EMBEDDINGS.items()}
    
    winning_domain = max(scores, key=scores.get)
    route_ms = int((time.perf_counter() - t_start) * 1000)
    return winning_domain, route_ms
