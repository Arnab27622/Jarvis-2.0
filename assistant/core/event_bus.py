"""
Module for handling events and commands in the system.
It provides an event bus for publishing and subscribing to events,
and a queue for handling typed text commands from the UI.
"""

from enum import Enum
import threading
from typing import Callable, Any
import queue

class EventType(Enum):
    """
    Enum representing different types of events in the system.
    These events can be used to notify other parts of the system about
    changes in the state or to trigger specific actions.
    """
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
    """
    Class representing an event bus, which allows different parts of the system
    to publish and subscribe to events. This enables loose coupling and makes
    it easier to add or remove features without affecting other parts of the system.
    """
    _subscribers: dict[EventType, list[Callable]]
    _lock: threading.Lock
    
    def __init__(self):
        """
        Initializes the event bus by creating an empty dictionary of subscribers
        and a lock for thread safety.
        """
        self._subscribers = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Subscribes a callback function to a specific event type.
        
        Args:
        event_type (EventType): The type of event to subscribe to.
        callback (Callable): The function to call when the event is emitted.
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def emit(self, event_type: EventType, data: Any = None) -> None:
        """
        Emits an event of a specific type, calling all subscribed callback functions.
        
        Args:
        event_type (EventType): The type of event to emit.
        data (Any): Optional data to pass to the callback functions.
        """
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
