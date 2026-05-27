import threading
from typing import Callable, Any
from enum import Enum

import queue

class EventType(Enum):
    # Voice/text output
    SPEAK = "speak"              # Jarvis is speaking (chat bubble)
    NOTIFY = "notify"            # Action confirmation (toast notification)
    
    # Input events
    USER_VOICE = "user_voice"    # User spoke via mic
    USER_TEXT = "user_text"      # User typed in UI
    
    # System status
    LISTENING = "listening"      # Mic is listening
    PROCESSING = "processing"    # Command is being processed
    LLM_STREAMING = "llm_stream" # LLM response tokens arriving
    
    # System info
    BATTERY_UPDATE = "battery"   # Battery status changed
    SYS_METRICS = "sys_metrics"  # CPU/RAM status changed
    COMMAND_EXECUTED = "cmd_done" # Command finished executing
    ERROR = "error"              # Something went wrong

class EventBus:
    _subscribers: dict[EventType, list[Callable]]
    _lock: threading.Lock
    
    def __init__(self):
        self._subscribers = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def emit(self, event_type: EventType, data: Any = None) -> None:
        with self._lock:
            listeners = self._subscribers.get(event_type, [])[:]
        for cb in listeners:
            try:
                cb(data)
            except Exception as e:
                print(f"[EventBus] Error in {event_type.value} handler: {e}")

# Singleton
bus = EventBus()

# Queue for typed text commands from UI
text_command_queue = queue.Queue()
