"""
Mouth Module - Unified Text-to-Speech (TTS) System

Now powered by Kokoro TTS for ultra-low latency streaming, with a clean
asynchronous background worker system to prevent main-thread blocking.

Provides two output channels:
  - speak()  : Always queues to TTS. For conversational content (LLM, weather, jokes).
  - notify() : Speaks when idle, prints to console when voice is busy.
               For quick action confirmations (open app, volume change, etc.).
"""

import sys
import time
import queue
import threading
import sounddevice as sd
from kokoro_onnx import Kokoro
import asyncio

# --- Global State ---
KOKORO_MODEL_PATH = "models/kokoro-v1.0.onnx"
KOKORO_VOICES_PATH = "models/voices-v1.0.bin"
VOICE_NAME = "am_michael"

print("Initializing Voice Module (Kokoro)...")
try:
    kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
    kokoro_ready = True
except Exception as e:
    print(f"Failed to load Kokoro model: {e}")
    kokoro_ready = False

tts_queue = queue.Queue()
_is_tts_running = False
_is_voice_busy = False
tts_thread = None
tts_loop = None

def print_animated_message(message: str) -> None:
    """
    Print a message to the console character by character for a typing effect.
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)
    print()

async def _stream_audio_and_text(text: str) -> None:
    """
    Generate audio stream using Kokoro TTS and synchronize it with console text printing.
    """
    if not kokoro_ready:
        await asyncio.to_thread(print_animated_message, text)
        return

    try:
        # Prepare the text animation thread, but don't start it yet
        print_thread = threading.Thread(target=print_animated_message, args=(text,))

        # Generate and play audio chunks as they arrive
        stream = kokoro.create_stream(text, voice=VOICE_NAME, speed=1.1, lang="en-us")
        
        first_chunk = True
        async for item in stream:
            if isinstance(item, tuple):
                chunk, _ = item
            else:
                chunk = item
                
            if first_chunk:
                # Play the chunk first, which initializes the audio device
                sd.play(chunk, samplerate=24000)
                await asyncio.sleep(0.3) # Give audio device time to actually start outputting sound
                # Now start printing so it matches the sound
                print_thread.start()
                first_chunk = False
                await asyncio.to_thread(sd.wait)
            else:
                # play chunk blocking so they queue up properly
                sd.play(chunk, samplerate=24000)
                await asyncio.to_thread(sd.wait)

        # Fallback if no audio was generated for some reason
        if first_chunk:
            print_thread.start()

        await asyncio.to_thread(print_thread.join)
    except Exception as e:
        print(f"Kokoro Streaming Error: {e}")
        # fallback to just printing if playback fails
        await asyncio.to_thread(print_animated_message, text)

async def _tts_worker() -> None:
    """Background worker that continuously consumes from the TTS queue."""
    global _is_tts_running, _is_voice_busy
    while _is_tts_running:
        try:
            # Non-blocking get inside the async loop
            sentence = await asyncio.to_thread(tts_queue.get, True, 1.0)
            _is_voice_busy = True
            await _stream_audio_and_text(sentence)
            _is_voice_busy = False
            tts_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            _is_voice_busy = False
            print(f"Streaming error: {e}")

def _start_tts_loop():
    """Runs the dedicated TTS event loop in a background thread."""
    global tts_loop
    tts_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(tts_loop)
    tts_loop.run_until_complete(_tts_worker())
    tts_loop.close()

def start_tts_consumer() -> None:
    """Start the background TTS consumer thread."""
    global _is_tts_running, tts_thread
    if not _is_tts_running:
        _is_tts_running = True
        tts_thread = threading.Thread(target=_start_tts_loop, daemon=True)
        tts_thread.start()

def stop_tts_consumer() -> None:
    """Stop the background TTS consumer thread."""
    global _is_tts_running
    _is_tts_running = False

def speak(text: str) -> None:
    """
    Unified entry point for Jarvis's voice.
    Always queues text to TTS. Use for conversational content
    (LLM responses, weather, jokes, news, etc.).
    """
    if not _is_tts_running:
        start_tts_consumer()
    tts_queue.put(text)

def notify(text: str) -> None:
    """
    For quick action confirmations (open app, volume, brightness, etc.).
    Speaks when voice is idle, prints to console when voice is busy.
    In a future UI, this becomes a toast notification.
    """
    if _is_voice_busy or not tts_queue.empty():
        print(f"[Jarvis] {text}")
    else:
        speak(text)

def speak_streaming(sentences: list[str]) -> None:
    """Streams a list of sentences to the TTS consumer."""
    if not _is_tts_running:
        start_tts_consumer()
        
    # Clear queue of any previous items to prioritize this stream
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
            tts_queue.task_done()
        except queue.Empty:
            break

    for s in sentences:
        if s.strip():
            tts_queue.put(s)

def wait_for_tts_completion() -> None:
    """Block until all sentences in the TTS queue have been spoken."""
    tts_queue.join()

if __name__ == "__main__":
    speak("System consolidation complete. I am now using a unified voice module powered by Kokoro.")
    wait_for_tts_completion()
