"""
Speak Selector Module - Dynamic TTS Engine Selection

This module provides intelligent selection between online and offline text-to-speech
engines based on internet connectivity. It serves as a facade pattern that abstracts
the underlying TTS implementation, allowing seamless switching between cloud-based
and local TTS services.

Key Features:
- Automatic detection of internet connectivity
- Dynamic import of appropriate TTS engine
- Consistent API across online and offline modes
- Fallback to offline TTS when internet is unavailable
- Support for both single and streaming TTS operations

Usage:
    from assistant.core.speak_selector import speak, speak_streaming

Dependencies:
- check_status: Internet connectivity detection
- mouth: Online TTS using Edge TTS
- mouth2: Offline TTS using pyttsx3
"""

from assistant.activities.check_status import is_online

# Check internet connectivity at module import time
online = is_online()

if online:
    # Import online TTS functions from mouth.py (Edge TTS)
    from assistant.core.mouth import (
        speak,
        speak_streaming,
        wait_for_tts_completion,
        start_tts_consumer,
        stop_tts_consumer,
    )
else:
    # Import offline TTS functions from mouth2.py (pyttsx3)
    from assistant.core.mouth2 import (
        speak,
        speak_streaming,
        wait_for_tts_completion,
        start_tts_consumer,
        stop_tts_consumer,
    )
