# app/pipeline.py
import asyncio
import time
import uuid
from dataclasses import dataclass
from app.asr import transcribe_stream
from app.tts import stream_tts
from app.rewriter import rewrite_query
from app.router import route_query
from agent.graph import agent_graph
from app.config import settings


@dataclass
class LatencyReport:
    turn_id: str
    transcript: str
    response_text: str
    agent_used: str = 'direct'
    asr_ms: int = 0
    rewrite_ms: int = 0
    route_ms: int = 0
    llm_ttft_ms: int = 0
    tts_ttfb_ms: int = 0
    total_ms: int = 0
    within_budget: bool = True
    error: str = ''

    def breakdown(self) -> dict:
        return {
            'turn_id': self.turn_id,
            'transcript': self.transcript,
            'response_text': self.response_text,
            'agent_used': self.agent_used,
            'asr_ms': self.asr_ms,
            'rewrite_ms': self.rewrite_ms,
            'route_ms': self.route_ms,
            'llm_ttft_ms': self.llm_ttft_ms,
            'tts_ttfb_ms': self.tts_ttfb_ms,
            'total_ms': self.total_ms,
            'within_budget': self.within_budget,
            'error': self.error}


async def run_turn(
    audio_queue: asyncio.Queue,
    audio_out_queue: asyncio.Queue,
    conversation_history: list[dict],
    turn_id: str,
    session_id: str) -> LatencyReport:

    report = LatencyReport(turn_id=turn_id, transcript='', response_text='')

    # Step 1 — ASR
    try:
        transcript, asr_ms = await transcribe_stream(audio_queue)
        report.transcript = transcript
        report.asr_ms = asr_ms
    except TimeoutError as e:
        report.error = str(e)
        await audio_out_queue.put(None)
        return report

    # Step 2 — Query rewriting
    sub_queries, rewrite_ms = await rewrite_query(transcript)
    report.rewrite_ms = rewrite_ms

    # Step 3 — Semantic routing
    route, route_ms = route_query(sub_queries)
    report.route_ms = route_ms
    report.agent_used = route
    print(f'transcript: "{transcript}"')
    print(f'sub_queries: {sub_queries}')
    print(f'route: {route} ({route_ms}ms)')

    # Step 4 — Agent invocation with pre-filled route
    final_state = await agent_graph.ainvoke(
            {'transcript': transcript,
            'sub_queries': sub_queries,
            'conversation_history': conversation_history,
            'route': route,
            'memory_hint': '',
            'tool_result': '',
            'tool_latency_ms': 0,
            'response_text': '',
            'llm_ttft_ms': 0,
            'agent_decision_ms': 0,
            'route_reason': '',
            'error': ''},
        config={'configurable': {'thread_id': session_id}})
    
    print(f'[agent] tool_result: "{final_state.get("tool_result", "EMPTY")}"')
    print(f'[agent] response: "{final_state.get("response_text", "EMPTY")[:100]}"')

    response_text = final_state['response_text']
    report.response_text = response_text
    report.llm_ttft_ms = final_state['llm_ttft_ms']

    # Step 5 — TTS
    tts_text_queue = asyncio.Queue()

    async def forward_tokens():
        if response_text:
            await tts_text_queue.put(response_text)
        await tts_text_queue.put(None)

    forward_task = asyncio.create_task(forward_tokens())
    try:
        tts_ttfb_ms = await stream_tts(tts_text_queue, audio_out_queue)
    except Exception as e:
        print(f'TTS error: {e}')
        tts_ttfb_ms = 0
        await audio_out_queue.put(None)
    await forward_task

    report.tts_ttfb_ms = tts_ttfb_ms
    report.total_ms = (report.asr_ms + report.rewrite_ms + report.route_ms +
                    report.llm_ttft_ms + report.tts_ttfb_ms)
    report.within_budget = report.total_ms <= settings.total_latency_budget_ms

    # Step 6 — Store turn in semantic memory
    from app.memory import semantic_memory, MemoryEntry
    semantic_memory.store(MemoryEntry(
        turn_id=turn_id,
        transcript=transcript,
        response=response_text,
        agent_used=route,
        timestamp=time.time()))

    return report
