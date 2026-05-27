import asyncio
import os
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from assistant.core.event_bus import bus, EventType, text_command_queue

app = FastAPI()

# Store connected clients
connected_clients: List[WebSocket] = []

# Path to the built React UI
UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jarvis-ui", "dist")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "screenshots")

if os.path.exists(UI_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(UI_DIR, "assets")), name="assets")

if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
    
if os.path.exists(SCREENSHOTS_DIR):
    app.mount("/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")

@app.get("/")
async def serve_index():
    with open(os.path.join(UI_DIR, "index.html"), "r") as f:
        return HTMLResponse(content=f.read())

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
server_loop = None

# This function bridges the sync event bus to the async websocket broadcast
def broadcast_event(event_type: EventType, data: dict = None):
    if not manager.active_connections or not server_loop:
        return
    
    try:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": event_type.value,
                "data": data or {}
            }),
            server_loop
        )
    except Exception as e:
        print(f"[Web] Broadcast error: {e}")

# Subscribe to all relevant events from the bus
def setup_event_bridge():
    bus.subscribe(EventType.SPEAK, lambda data: broadcast_event(EventType.SPEAK, data))
    bus.subscribe(EventType.NOTIFY, lambda data: broadcast_event(EventType.NOTIFY, data))
    bus.subscribe(EventType.USER_VOICE, lambda data: broadcast_event(EventType.USER_VOICE, data))
    bus.subscribe(EventType.LISTENING, lambda data: broadcast_event(EventType.LISTENING, {"listening": data}))
    bus.subscribe(EventType.BATTERY_UPDATE, lambda data: broadcast_event(EventType.BATTERY_UPDATE, data))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global server_loop
    server_loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "command":
                text = data.get("data", {}).get("text", "")
                if text:
                    # Echo the text back to UI immediately
                    await manager.broadcast({
                        "type": EventType.USER_TEXT.value,
                        "data": {"text": text}
                    })
                    # Put it in the queue for JARVIS to process
                    print(f"[Debug] server.py putting text in queue: {text}")
                    text_command_queue.put(text)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def start_web_server(port: int = 1410):
    setup_event_bridge()
    print(f"Starting JARVIS Web Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")
