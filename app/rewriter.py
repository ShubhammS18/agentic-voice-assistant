import time
from datetime import datetime
from anthropic import AsyncAnthropic
from app.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

REWRITE_PROMPT = """You are a query rewriter. Today's date is {today}.
Given a user query, produce 2-3 specific search sub-queries that clarify the intent.
Always produce sub-queries even for vague or conversational inputs.
If the query references previous conversation, produce sub-queries about the likely topic.

Output ONLY the sub-queries, one per line. No explanation. No refusals.

Query: {query}
Sub-queries:"""

async def rewrite_query(transcript: str) -> tuple[list[str], int]:
    """Returns (sub_queries, rewrite_ms)"""
    t_start = time.perf_counter()
    message = await client.messages.create(
        model=settings.llm_model,
        max_tokens=80,
        messages=[{
            "role": "user",
            "content": REWRITE_PROMPT.format(
                today=datetime.now().strftime("%B %d, %Y"),
                query=transcript)}])
    
    raw = message.content[0].text.strip()
    sub_queries = [q.strip() for q in raw.split('\n') if q.strip()][:3]
    if not sub_queries:
        sub_queries = [transcript]
    rewrite_ms = int((time.perf_counter() - t_start) * 1000)
    return sub_queries, rewrite_ms