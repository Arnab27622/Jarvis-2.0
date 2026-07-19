"""
FastAPI web server providing a real-time dashboard and WebSocket interface for JARVIS.
"""

import asyncio
import os
import psutil
try:
    import GPUtil
except ImportError:
    GPUtil = None
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
import uvicorn
from assistant.core.event_bus import bus, EventType, text_command_queue
from assistant.core.config import config

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

# Global network IO trackers
_last_net_io = None
_last_net_time = None

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the server starts."""
    asyncio.create_task(metrics_emitter())

async def metrics_emitter():
    """Periodically collects and broadcasts system metrics."""
    global _last_net_io, _last_net_time
    import time
    
    # Prime the CPU percent counter so first read isn't 0
    psutil.cpu_percent()
    
    # Simple Exponential Moving Average (EMA) to smooth network speeds
    ema_upload = 0.0
    ema_download = 0.0
    alpha = 0.3  # Smoothing factor (lower = smoother but slower to react)
    
    while True:
        try:
            if manager.active_connections:
                current_io = psutil.net_io_counters()
                current_time = time.time()
                
                upload_speed = 0
                download_speed = 0
                
                if _last_net_io and _last_net_time:
                    dt = current_time - _last_net_time
                    if dt > 0:
                        upload_speed = (current_io.bytes_sent - _last_net_io.bytes_sent) / dt
                        download_speed = (current_io.bytes_recv - _last_net_io.bytes_recv) / dt
                        
                # Apply EMA
                if ema_upload == 0 and ema_download == 0:
                    ema_upload = upload_speed
                    ema_download = download_speed
                else:
                    ema_upload = (alpha * upload_speed) + ((1 - alpha) * ema_upload)
                    ema_download = (alpha * download_speed) + ((1 - alpha) * ema_download)
                        
                _last_net_io = current_io
                _last_net_time = current_time
                
                # Determine proper disk path based on OS
                disk_path = 'C:\\' if os.name == 'nt' else '/'
                
                metrics = {
                    "cpu": psutil.cpu_percent(interval=None),
                    "ram": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage(disk_path).percent,
                    "network": {
                        "upload": ema_upload,
                        "download": ema_download
                    }
                }
                
                if GPUtil:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        metrics["gpu"] = gpus[0].load * 100
                else:
                    metrics["gpu"] = 0
                
                await manager.broadcast({
                    "type": EventType.SYS_METRICS.value,
                    "data": metrics
                })
        except Exception:
            pass
        await asyncio.sleep(2)

@app.get("/")
async def serve_index():
    """Serves the main React application entry point."""
    with open(os.path.join(UI_DIR, "index.html"), "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/settings")
async def get_settings():
    return JSONResponse({
        "tts_voice": config.tts_voice,
        "tts_speed": config.tts_speed,
        "theme": config.theme
    })

@app.post("/api/settings")
async def update_settings(request: Request):
    data = await request.json()
    old_theme = config.theme
    old_voice = config.tts_voice
    
    config.save_settings(data)
    
    # Broadcast changes to active clients only if they actually changed
    if data.get("theme") and data.get("theme") != old_theme:
        theme_names = {
            "cyan": "COLD LUXURY",
            "amber": "TERMINAL BRUTALISM",
            "minimal": "EDITORIAL MINIMALIST",
            "oled": "OLED BLACK"
        }
        friendly_name = theme_names.get(data['theme'], data['theme'].upper())
        broadcast_event(EventType.NOTIFY, {"text": f"Theme updated to {friendly_name}"})
    if data.get("tts_voice") and data.get("tts_voice") != old_voice:
        broadcast_event(EventType.NOTIFY, {"text": f"Voice updated to {data['tts_voice'].upper()}"})
        
    return JSONResponse({"status": "success", "settings": data})

@app.get("/api/status")
async def get_status():
    return JSONResponse({
        "providers": config.get_available_llm_providers(),
        "status": "online",
        "stt": "Google Web Speech",
        "tts": "Kokoro TTS"
    })

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    global IS_AUTHENTICATED
    if not IS_AUTHENTICATED:
        return JSONResponse({"status": "error", "message": "Unauthorized. Please authenticate first."}, status_code=401)
        
    try:
        from assistant.LLM.model import ingest_document
        import shutil
        import threading
        
        doc_dir = config.brain_data_dir / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        file_path = doc_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ingest in background so UI isn't blocked
        threading.Thread(target=ingest_document, args=(str(file_path),)).start()
        
        return JSONResponse({"status": "success", "message": f"Processing {file.filename} into RAG memory."})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

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
IS_AUTHENTICATED = False

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
    bus.subscribe(EventType.PERMISSION_REQUEST, lambda data: broadcast_event(EventType.PERMISSION_REQUEST, data))
    
    # Auth events
    def handle_auth_success(data):
        global IS_AUTHENTICATED
        IS_AUTHENTICATED = True
        broadcast_event(EventType.AUTH_SUCCESS, data)
        
    bus.subscribe(EventType.AUTH_STATUS, lambda data: broadcast_event(EventType.AUTH_STATUS, data))
    bus.subscribe(EventType.AUTH_SUCCESS, handle_auth_success)
    bus.subscribe(EventType.AUTH_FAILED, lambda data: broadcast_event(EventType.AUTH_FAILED, data))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles bidirectional WebSocket communication for commands and status updates."""
    global server_loop
    server_loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    
    if IS_AUTHENTICATED:
        await websocket.send_json({"type": "auth_success", "data": {}})
        
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            if not IS_AUTHENTICATED:
                await websocket.send_json({"type": "error", "data": {"message": "Unauthorized. Please authenticate first."}})
                continue
                
            if msg_type == "command":
                text = data.get("data", {}).get("text", "")
                if text:
                    # Pass input directly, React handles XSS escaping on the frontend
                    clean_text = text.strip()
                    if clean_text:
                        await manager.broadcast({
                            "type": EventType.USER_TEXT.value,
                            "data": {"text": clean_text}
                        })
                        print(f"[Debug] server.py putting text in queue: {clean_text}")
                        text_command_queue.put(clean_text)
                        
            elif msg_type == "permission_response":
                from assistant.core.event_bus import permission_queue
                approved = data.get("data", {}).get("approved", False)
                permission_queue.put(approved)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def start_web_server(port: int = 1410):
    """Initializes the event bridge and starts the Uvicorn server."""
    setup_event_bridge()
    print(f"Starting JARVIS Web Server on port {port}...")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
