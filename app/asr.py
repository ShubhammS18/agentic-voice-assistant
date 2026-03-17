import asyncio, time
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from app.config import settings


async def transcribe_stream(audio_queue: asyncio.Queue) -> tuple[str, int]:
    client = DeepgramClient(settings.deepgram_api_key)
    transcript_parts: list[str] = []
    final_event = asyncio.Event()
    t_start = time.perf_counter()
    t_final = 0.0

    connection = client.listen.asyncwebsocket.v('1')

    async def on_transcript(self, **kwargs):
        nonlocal t_final
        result = kwargs.get('result')
        if result is None:
            return
        alt = result.channel.alternatives[0]
        if alt.transcript and result.is_final:
            transcript_parts.append(alt.transcript)
            t_final = time.perf_counter()
            if result.speech_final:
                final_event.set()

    async def on_utterance_end(self, **kwargs):
        if transcript_parts:
            final_event.set()

    async def on_error(self, **kwargs):
        error = kwargs.get('error')
        print(f'[Deepgram error] {error}')
        final_event.set()

    connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model=settings.asr_model,
        encoding='linear16',
        sample_rate=16000,
        channels=1,
        punctuate=True,
        interim_results=True,
        utterance_end_ms=1000)

    await connection.start(options)

    async def send_audio():
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                await connection.finish()
                break
            await connection.send(chunk)

    send_task = asyncio.create_task(send_audio())

    try:
        await asyncio.wait_for(
            final_event.wait(),
            timeout=settings.asr_timeout_ms / 1000)
    except asyncio.TimeoutError:
        raise TimeoutError(f'ASR timeout after {settings.asr_timeout_ms}ms')
    finally:
        send_task.cancel()

    if t_final == 0.0:
        t_final = time.perf_counter()

    transcript = ' '.join(transcript_parts).strip()
    asr_ms = int((t_final - t_start) * 1000)
    return transcript, asr_ms