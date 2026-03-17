import asyncio, time
from anthropic import AsyncAnthropic
from app.config import settings


client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def stream_response(transcript: str, history: list[dict]) -> tuple[asyncio.Queue, asyncio.Event]:
    '''Day 1 only — replaced by agent/graph.py in Phase 2.'''
    token_queue = asyncio.Queue()
    done_event = asyncio.Event()
    t_start = time.perf_counter()


    async def _stream():
        async with client.messages.stream(
            model=settings.llm_model,
            max_tokens=300,
            system=settings.voice_system_prompt,
            messages=history + [{"role": "user", "content": transcript}]) as stream:
            async for token in stream.text_stream:
                await token_queue.put(token)
        await token_queue.put(None)
        done_event.set()


    asyncio.create_task(_stream())
    return token_queue, done_event
