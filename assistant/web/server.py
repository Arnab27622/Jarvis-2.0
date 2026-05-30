"""
FastAPI web server providing a real-time dashboard and WebSocket interface for JARVIS.
"""

import asyncio
import os
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from assistant.core.event_bus import bus, EventType, text_command_queue

app = FastAPI()

connected_clients: List[WebSocket] = []

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
    """Serves the main React application entry point."""
    with open(os.path.join(UI_DIR, "index.html"), "r") as f:
        return HTMLResponse(content=f.read())

class ConnectionManager:
    """Manages active WebSocket connections and message broadcasting."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts a new connection and adds it to the active list."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Removes a connection from the active list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Sends a JSON message to all connected clients."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
server_loop = None

def broadcast_event(event_type: EventType, data: dict = None):
    """Bridges synchronous event bus signals to asynchronous WebSocket broadcasts."""
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

def setup_event_bridge():
    """Registers event bus subscribers to forward system events to the UI."""
    bus.subscribe(EventType.SPEAK, lambda data: broadcast_event(EventType.SPEAK, data))
    bus.subscribe(EventType.NOTIFY, lambda data: broadcast_event(EventType.NOTIFY, data))
    bus.subscribe(EventType.USER_VOICE, lambda data: broadcast_event(EventType.USER_VOICE, data))
    bus.subscribe(EventType.USER_TEXT, lambda data: broadcast_event(EventType.USER_TEXT, data))
    bus.subscribe(EventType.BATTERY_UPDATE, lambda data: broadcast_event(EventType.BATTERY_UPDATE, data))
    bus.subscribe(EventType.SYS_METRICS, lambda data: broadcast_event(EventType.SYS_METRICS, data))
    bus.subscribe(EventType.LISTENING, lambda data: broadcast_event(EventType.LISTENING, {"listening": data if isinstance(data, bool) else data.get("state", False)}))
    bus.subscribe(EventType.PROCESSING, lambda data: broadcast_event(EventType.PROCESSING, {"state": data.get("state", False)}))
    bus.subscribe(EventType.COMMAND_EXECUTED, lambda data: broadcast_event(EventType.COMMAND_EXECUTED, data))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles bidirectional WebSocket communication for commands and status updates."""
    global server_loop
    server_loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "command":
                text = data.get("data", {}).get("text", "")
                if text:
                    await manager.broadcast({
                        "type": EventType.USER_TEXT.value,
                        "data": {"text": text}
                    })
                    print(f"[Debug] server.py putting text in queue: {text}")
                    text_command_queue.put(text)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def start_web_server(port: int = 1410):
    """Initializes the event bridge and starts the Uvicorn server."""
    setup_event_bridge()
    print(f"Starting JARVIS Web Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")
