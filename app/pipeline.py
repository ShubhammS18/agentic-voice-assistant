import asyncio, time, uuid
from dataclasses import dataclass
from app.asr import transcribe_stream
from app.llm import stream_response
from app.tts import stream_tts
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
        print(f'[DEBUG] transcript: "{transcript}" asr_ms: {asr_ms}')
    except TimeoutError as e:
        print(f'[DEBUG] ASR timeout: {e}')
        report.error = str(e)
        await audio_out_queue.put(None)
        return report

    # Step 2 — LLM only (skip TTS for now)
    token_queue, done_event = await stream_response(transcript, conversation_history)
    t_llm_start = time.perf_counter()
    first_token = True
    full_response = ''
    llm_ttft_ms = 0

    while True:
        token = await token_queue.get()
        if token is None:
            break
        if first_token:
            llm_ttft_ms = int((time.perf_counter() - t_llm_start) * 1000)
            first_token = False
        full_response += token

    print(f'[DEBUG] response: "{full_response}" llm_ttft_ms: {llm_ttft_ms}')

    report.response_text = full_response
    report.llm_ttft_ms = llm_ttft_ms
    report.tts_ttfb_ms = 0  # skipped for now
    report.total_ms = report.asr_ms + report.llm_ttft_ms
    report.within_budget = report.total_ms <= settings.total_latency_budget_ms

    await audio_out_queue.put(None)  # signal no audio coming
    return report