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

@app.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    conversation_history = []

    try:
        audio_queue = asyncio.Queue()
        audio_out_queue = asyncio.Queue()

        async def receive_audio():
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    await audio_queue.put(None)
                    break
                elif message["type"] == "websocket.receive":
                    if "bytes" in message and message["bytes"]:
                        await audio_queue.put(message["bytes"])
                    elif "text" in message and message["text"] == "END":
                        await audio_queue.put(None)
                        break

        # Start receiving audio BEFORE calling run_turn
        # so audio flows into the queue while ASR is processing
        receive_task = asyncio.create_task(receive_audio())

        try:
            report = await run_turn(
                    audio_queue=audio_queue,
                    audio_out_queue=audio_out_queue,
                    conversation_history=conversation_history,
                    turn_id=str(uuid.uuid4()),
                    session_id=session_id)

            await websocket.send_json({"type": "latency",**report.breakdown()})

            conversation_history.append({"role": "user", "content": report.transcript})
            conversation_history.append({"role": "assistant", "content": report.response_text})

        except Exception as e:
            print(f'[DEBUG] run_turn error: {e}')
            await websocket.send_json({"type": "error", "message": str(e)})
        finally:
            receive_task.cancel()

    except WebSocketDisconnect:
        pass