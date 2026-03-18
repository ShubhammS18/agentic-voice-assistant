# app/api.py
import asyncio
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.pipeline import run_turn
from app.config import settings

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
def health():
    return {"status": "ok", "model": settings.llm_model}

# Session memory persists across WebSocket connections for the same session_id
_sessions: dict[str, list[dict]] = {}

@app.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Browser sends session_id as query param to persist conversation history
    session_id = websocket.query_params.get("session_id", str(uuid.uuid4()))
    if session_id not in _sessions:
        _sessions[session_id] = []
    conversation_history = _sessions[session_id]

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
            session_id=session_id,
        )

        # Drain audio
        while True:
            chunk = await audio_out_queue.get()
            if chunk is None:
                break
            await websocket.send_text(
                '{"type":"audio","data":"' + chunk + '"}'
            )

        await websocket.send_json({
            "type": "latency",
            **report.breakdown()
        })

        if report.transcript:
            conversation_history.append({
                "role": "user",
                "content": report.transcript
            })
            conversation_history.append({
                "role": "assistant",
                "content": report.response_text
            })

    except Exception as e:
        print(f'[api] error: {e}')
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass