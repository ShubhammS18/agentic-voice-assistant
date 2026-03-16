import asyncio, time
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from app.config import settings


async def transcribe_stream(audio_queue: asyncio.Queue) -> tuple[str, int]:
    '''
    Consume raw audio bytes from audio_queue.
    Returns (transcript: str, asr_ms: int) when utterance is complete.

    audio_queue: asyncio.Queue feeding raw PCM bytes (16kHz, 16-bit, mono)
    Returns: final transcript text and latency in milliseconds
    '''
    client = DeepgramClient(settings.deepgram_api_key)
    transcript_parts: list[str] = []
    final_event = asyncio.Event()
    t_start = time.perf_counter()
    t_final = 0.0

    connection = client.listen.asyncwebsocket.v('1')

    async def on_transcript(result, **kwargs):
        nonlocal t_final
        alt = result.channel.alternatives[0]
        if alt.transcript and result.is_final:
            transcript_parts.append(alt.transcript)
            t_final = time.perf_counter()
            if result.speech_final:
                final_event.set()

    async def on_utterance_end(result, **kwargs):
        # Fires after utterance_end_ms of silence — catches cases
        # where speech_final never arrives
        if transcript_parts:
            final_event.set()

    async def on_error(error, **kwargs):
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
        utterance_end_ms=1000,
        speech_final=True)

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

    # Use t_start as fallback if t_final was never set
    if t_final == 0.0:
        t_final = time.perf_counter()

    transcript = ' '.join(transcript_parts).strip()
    asr_ms = int((t_final - t_start) * 1000)
    return transcript, asr_ms