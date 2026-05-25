"""
Speak Selector Module - Unified TTS Interface

This module provides a consistent interface for the assistant's voice,
now powered by the local Kokoro ONNX model for ultra-low latency streaming.
"""

from assistant.core.mouth import (
    speak,
    speak_streaming,
    wait_for_tts_completion,
    start_tts_consumer,
    stop_tts_consumer,
)
