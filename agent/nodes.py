import time
import asyncio
from anthropic import AsyncAnthropic
from app.config import settings
from agent.state import AgentState

client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def orchestrator_node(state: AgentState) -> AgentState:
    """Route pre-filled by semantic router. Just retrieve semantic memory."""
    from app.memory import semantic_memory
    past_context = semantic_memory.retrieve(state['transcript'])
    memory_hint = ''
    if past_context:
        memory_hint = '\n'.join([
            f"Past turn: Q: {m.transcript} A: {m.response[:100]}"
            for m in past_context])
    return {**state, 'memory_hint': memory_hint, 'agent_decision_ms': 0}


async def call_rag_node(state: AgentState) -> AgentState:
    """Call the RAG tool directly."""
    import httpx
    t_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.post(
                'http://localhost:8000/ask',
                json={'question': state['transcript']})
            data = response.json()
            tool_result = f"{data['answer']} (verdict: {data['verdict']})"
    except Exception as e:
        tool_result = f"RAG unavailable: {e}"
    tool_latency_ms = int((time.perf_counter() - t_start) * 1000)
    return {**state, 'tool_result': tool_result, 'tool_latency_ms': tool_latency_ms}


async def call_web_node(state: AgentState) -> AgentState:
    """Call DuckDuckGo directly."""
    from ddgs import DDGS
    t_start = time.perf_counter()
    query = state['sub_queries'][0] if state.get('sub_queries') else state['transcript']
    try:
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=3))
        results = await asyncio.to_thread(_search)
        snippets = [f"{r['title']}: {r['body'][:200]}" for r in results]
        tool_result = ' '.join(snippets)
    except Exception as e:
        tool_result = f"Web search unavailable: {e}"
        print(f'web search error: {e}')
    tool_latency_ms = int((time.perf_counter() - t_start) * 1000)
    return {**state, 'tool_result': tool_result, 'tool_latency_ms': tool_latency_ms}


async def call_data_node(state: AgentState) -> AgentState:
    """Look up structured data directly."""
    from mcp_servers.data_server import DATA_STORE
    t_start = time.perf_counter()
    query = state['transcript'].lower()
    key = 'tech_stack'
    for k in ['latency_budget', 'supported_languages',
            'routing_method', 'web_search_provider']:
        if k.replace('_', ' ') in query:
            key = k
            break
    tool_result = DATA_STORE.get(key, f'No data found for key: {key}')
    tool_latency_ms = int((time.perf_counter() - t_start) * 1000)
    return {**state, 'tool_result': tool_result, 'tool_latency_ms': tool_latency_ms}


async def synthesize_node(state: AgentState) -> AgentState:
    """Turn tool result into a voice-appropriate response."""
    t_start = time.perf_counter()
    ttft_recorded = False
    context = state.get('tool_result', '')
    memory = state.get('memory_hint', '')
    history = state.get('conversation_history', [])

    synthesis_prompt = (
        f"User asked: {state['transcript']}\n"
        + (f"Relevant past context: {memory}\n" if memory else '')
        + (f"Information from {state['route']} tool: {context}\n" if context else '')
        + "Respond in 2-3 natural spoken sentences. No markdown. No lists. Only use the information provided. Do not add anything from your own knowledge.")

    full_response = ''
    llm_ttft_ms = 0

    async with client.messages.stream(
        model=settings.llm_model,
        max_tokens=300,
        system=settings.voice_system_prompt,
        messages=history + [{'role': 'user', 'content': synthesis_prompt}]) as stream:
        async for token in stream.text_stream:
            if not ttft_recorded:
                llm_ttft_ms = int((time.perf_counter() - t_start) * 1000)
                ttft_recorded = True
            full_response += token

    return {**state, 'response_text': full_response, 'llm_ttft_ms': llm_ttft_ms}