import asyncio
import uuid
import os
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.pipeline import run_turn
from app.config import settings
from app.resilience import circuit_breaker, FallbackReason, FALLBACK_MESSAGES

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
def health():
    return {
        "status": "ok",
        "models": {
            "asr": settings.asr_model,
            "llm": settings.llm_model,
            "tts": settings.tts_model},
        "circuit_breakers": {
            "asr": circuit_breaker.get_status("asr"),
            "agent": circuit_breaker.get_status("agent"),
            "tts": circuit_breaker.get_status("tts")},
        "mcp_servers": {
            "rag":  f"localhost:{settings.rag_mcp_port}",
            "web":  f"localhost:{settings.websearch_mcp_port}",
            "data": f"localhost:{settings.data_mcp_port}"},
        "latency_budget_ms": settings.total_latency_budget_ms}

@app.post("/replay")
async def replay(file: UploadFile = File(...)):
    """
    Feed a recorded WAV file through the full pipeline.
    Useful for debugging and benchmarking without a microphone.
    """
    audio_data = await file.read()
    audio_queue = asyncio.Queue()
    audio_out_queue = asyncio.Queue()

    # Feed WAV bytes into audio queue in chunks
    chunk_size = 3200  # 100ms at 16kHz 16-bit mono
    for i in range(0, len(audio_data), chunk_size):
        await audio_queue.put(audio_data[i:i + chunk_size])
    await audio_queue.put(None)  # sentinel

    try:
        report = await run_turn(
            audio_queue=audio_queue,
            audio_out_queue=audio_out_queue,
            conversation_history=[],
            turn_id=str(uuid.uuid4()),
            session_id="replay-" + str(uuid.uuid4()))

        # Save replay result
        os.makedirs("replay/recorded_inputs", exist_ok=True)
        replay_id = str(uuid.uuid4())[:8]
        save_path = f"replay/recorded_inputs/{replay_id}.wav"
        with open(save_path, "wb") as f:
            f.write(audio_data)

        return JSONResponse({
            "status": "ok",
            "saved_as": save_path,
            **report.breakdown()})

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# Session memory persists across WebSocket connections for the same session_id
_sessions: dict[str, list[dict]] = {}

@app.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()

    session_id = websocket.query_params.get("session_id", str(uuid.uuid4()))
    if session_id not in _sessions:
        _sessions[session_id] = []
    conversation_history = _sessions[session_id]

    # Check circuit breakers before doing anything
    if circuit_breaker.is_open("asr"):
        await websocket.send_json({
            "type": "error",
            "message": FALLBACK_MESSAGES[FallbackReason.ASR_TIMEOUT]})
        await websocket.close()
        return

    audio_queue = asyncio.Queue()
    audio_out_queue = asyncio.Queue()

    async def receive_audio():
        while True:
            try:
                message = await websocket.receive()
            except Exception:
                await audio_queue.put(None)
                break
            if message["type"] == "websocket.disconnect":
                await audio_queue.put(None)
                break
            elif message["type"] == "websocket.receive":
                if "bytes" in message and message["bytes"]:
                    await audio_queue.put(message["bytes"])
                elif "text" in message and message["text"] == "END":
                    await audio_queue.put(None)
                    break

    receive_task = asyncio.create_task(receive_audio())

    try:
        report = await run_turn(
            audio_queue=audio_queue,
            audio_out_queue=audio_out_queue,
            conversation_history=conversation_history,
            turn_id=str(uuid.uuid4()),
            session_id=session_id)

        # Record success for circuit breaker
        circuit_breaker.record_success("asr")

        # Drain audio output
        while True:
            chunk = await audio_out_queue.get()
            if chunk is None:
                break
            await websocket.send_text(
                '{"type":"audio","data":"' + chunk + '"}')

        await websocket.send_json({
            "type": "latency",
            **report.breakdown()})

        if report.transcript:
            conversation_history.append({
                "role": "user",
                "content": report.transcript})
            conversation_history.append({
                "role": "assistant",
                "content": report.response_text})

    except TimeoutError:
        circuit_breaker.record_failure("asr")
        try:
            await websocket.send_json({
                "type": "error",
                "message": FALLBACK_MESSAGES[FallbackReason.ASR_TIMEOUT]})
        except Exception:
            pass

    except Exception as e:
        print(f'[api] error: {e}')
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)})
        except Exception:
            pass

    finally:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass