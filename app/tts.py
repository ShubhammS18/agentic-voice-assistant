import asyncio, json, time
import websockets
from app.config import settings


async def stream_tts(text_queue: asyncio.Queue, audio_out_queue: asyncio.Queue) -> int:
    '''
    Consume text tokens from text_queue.
    Push base64-encoded audio chunks to audio_out_queue.
    Returns tts_ttfb_ms (time to first audio byte).
    '''
    ws_url = (
        f"wss://api.elevenlabs.io/v1/text-to-speech/"
        f"{settings.elevenlabs_voice_id}/stream-input"
        f"?model_id={settings.tts_model}&output_format=mp3_44100_128")
    t_start = time.perf_counter()
    ttfb_ms = 0
    first_audio = True


    async with websockets.connect(
        ws_url,
        additional_headers={"xi-api-key": settings.elevenlabs_api_key},
        ping_interval=20, ping_timeout=10) as ws:


        await ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            "generation_config": {"chunk_length_schedule": [120, 160, 250]}}))


        async def receive_audio():
            nonlocal ttfb_ms, first_audio
            async for message in ws:
                data = json.loads(message)
                audio_b64 = data.get("audio")
                if audio_b64:
                    if first_audio:
                        ttfb_ms = int((time.perf_counter() - t_start) * 1000)
                        first_audio = False
                    await audio_out_queue.put(audio_b64)
                if data.get("isFinal"):
                    await audio_out_queue.put(None)
                    break


        receive_task = asyncio.create_task(receive_audio())
        text_buffer = ""
        while True:
            item = await text_queue.get()
            if item is None:
                if text_buffer:
                    await ws.send(json.dumps({"text": text_buffer}))
                await ws.send(json.dumps({"text": "", "flush": True}))
                break
            if isinstance(item, tuple):
                continue
            text_buffer += item
            if len(text_buffer) >= 100 or any(text_buffer.endswith(p) for p in ['. ', '? ', '! ', ', ']):
                await ws.send(json.dumps({'text': text_buffer}))
            text_buffer = ''
        await receive_task


    if ttfb_ms == 0:        # fallback if no audio received
        ttfb_ms = int((time.perf_counter() - t_start) * 1000)
    return ttfb_ms
