"""
Speak Selector Module - Unified TTS Interface

This module provides a consistent interface for the assistant's voice,
now powered by a unified mouth module that handles online/offline
switching internally.
"""

from assistant.core.mouth import (
    speak,
    speak_streaming,
    wait_for_tts_completion,
    start_tts_consumer,
    stop_tts_consumer,
)
