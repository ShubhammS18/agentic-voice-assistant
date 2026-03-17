import time
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
    """Call the RAG MCP server."""
    t_start = time.perf_counter()
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    import subprocess, sys
    proc = subprocess.Popen(
        [sys.executable, 'mcp_servers/rag_server.py'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    async with stdio_client(proc.stdin, proc.stdout) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                'ask_documents', {'query': state['transcript']})
            tool_result = result.content[0].text
    tool_latency_ms = int((time.perf_counter() - t_start) * 1000)
    return {**state, 'tool_result': tool_result, 'tool_latency_ms': tool_latency_ms}


async def call_web_node(state: AgentState) -> AgentState:
    """Call the web search MCP server (DuckDuckGo)."""
    t_start = time.perf_counter()
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    import subprocess, sys
    proc = subprocess.Popen(
        [sys.executable, 'mcp_servers/websearch_server.py'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    async with stdio_client(proc.stdin, proc.stdout) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                'search_web', {'query': state['transcript']})
            tool_result = result.content[0].text
    tool_latency_ms = int((time.perf_counter() - t_start) * 1000)
    return {**state, 'tool_result': tool_result, 'tool_latency_ms': tool_latency_ms}


async def call_data_node(state: AgentState) -> AgentState:
    """Call the structured data MCP server."""
    t_start = time.perf_counter()
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    import subprocess, sys
    proc = subprocess.Popen(
        [sys.executable, 'mcp_servers/data_server.py'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    
    async with stdio_client(proc.stdin, proc.stdout) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Find best matching key from transcript
            query = state['transcript'].lower()
            key = 'tech_stack'  # default
            for k in ['latency_budget', 'supported_languages',
                    'routing_method', 'web_search_provider']:
                if k.replace('_', ' ') in query:
                    key = k
                    break
            result = await session.call_tool('lookup_structured', {'key': key})
            tool_result = result.content[0].text
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
        + "Respond in 2-3 natural spoken sentences. No markdown. No lists.")

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