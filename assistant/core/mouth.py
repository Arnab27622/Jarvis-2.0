"""
Mouth Module - Unified Text-to-Speech (TTS) System

Now powered by Kokoro TTS for ultra-low latency streaming, with a clean
asynchronous background worker system to prevent main-thread blocking.

Architecture (Pipelined):
  tts_queue (text) → Generator Worker → _playback_queue (audio) → Player Worker

Provides two output channels:
  - speak()  : Always queues to TTS. For conversational content (LLM, weather, jokes).
  - notify() : Speaks when idle, prints to console when voice is busy.
               For quick action confirmations (open app, volume change, etc.).
"""

import sys
import os
import time
import wave
import queue
import threading
import uuid
import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
import asyncio
from assistant.core.event_bus import bus, EventType
from assistant.core.config import config
from assistant.core.logger import get_logger

logger = get_logger("Mouth")

# --- Global State ---
KOKORO_MODEL_PATH = str(config.kokoro_model_path)
KOKORO_VOICES_PATH = str(config.kokoro_voices_path)

logger.info("Scheduling Voice Module (Kokoro) for background initialization...")

kokoro = None
kokoro_ready = False
_kokoro_load_event = threading.Event()

def _load_kokoro():
    global kokoro, kokoro_ready
    try:
        import torch
        import onnxruntime as ort
        
        # Workaround for Windows ONNXRuntime CUDA DLL issue
        if torch.cuda.is_available():
            torch.cuda.init()
        
        session = ort.InferenceSession(
            KOKORO_MODEL_PATH,
            providers=[
                "CUDAExecutionProvider",
                "CPUExecutionProvider"
            ]
        )
        kokoro = Kokoro.from_session(session, KOKORO_VOICES_PATH)
        kokoro_ready = True
        logger.info("Kokoro ready. Providers: %s", session.get_providers())
    except Exception as e:
        logger.error("Failed to load Kokoro model: %s", e)
        kokoro_ready = False
    finally:
        _kokoro_load_event.set()

# Start loading in background immediately
threading.Thread(target=_load_kokoro, daemon=True).start()

# --- Acknowledgment Chirp (uses pygame.mixer to avoid sounddevice TTS conflict) ---
ACK_SOUND_PATH = str(config.ack_sound_path)
_ack_pygame_sound = None

def _load_ack_sound():
    """Pre-load the acknowledgment chirp as a pygame Sound for instant, conflict-free playback."""
    global _ack_pygame_sound
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        if os.path.exists(ACK_SOUND_PATH):
            _ack_pygame_sound = pygame.mixer.Sound(ACK_SOUND_PATH)
            _ack_pygame_sound.set_volume(0.5)
            logger.info("Acknowledgment sound loaded (pygame).")
    except Exception as e:
        logger.warning("Could not load ack sound: %s", e)

_load_ack_sound()

def play_ack_sound() -> None:
    """Play the instant acknowledgment chirp (non-blocking, ~150ms). Uses pygame to avoid conflict with sounddevice TTS."""
    if _ack_pygame_sound is not None:
        try:
            _ack_pygame_sound.play()
        except Exception:
            pass  # Silently fail - this is just a UX enhancement

# --- Queues & State ---
tts_queue = queue.Queue()             # Stage 1: text items waiting for audio generation
_playback_queue = queue.Queue(maxsize=5)  # Stage 2: generated audio waiting for playback
_is_tts_running = False
_is_voice_busy = False
_generator_thread = None
_player_thread = None
_gen_loop = None
_current_message_id = None

# Sentinel to signal "end of stream" to the player
_STREAM_END = object()

def print_animated_message(message: str) -> None:
    """
    Print a message to the console character by character for a typing effect.
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)
    print()

def _generate_audio(text: str):
    """Synchronously generate audio from text using Kokoro. Returns (audio_array, sample_rate) or None."""
    # Wait for Kokoro to load if this is called early
    if not _kokoro_load_event.wait(timeout=15.0) or not kokoro_ready:
        return None
    try:
        from assistant.core.llm_utils import clean_for_speech
        tts_text = clean_for_speech(text)
        if not tts_text.strip():
            return None
        audio, _ = kokoro.create(tts_text, voice=config.tts_voice, speed=config.tts_speed, lang=config.tts_language)
        return audio
    except Exception as e:
        logger.error("Kokoro generation error: %s", e)
        return None

async def _tts_generator_worker() -> None:
    """
    Stage 1: Continuously takes text from tts_queue, generates audio with Kokoro,
    and pushes the result to _playback_queue for the player to consume.
    """
    global _is_tts_running
    while _is_tts_running:
        try:
            item = await asyncio.to_thread(tts_queue.get, True, 1.0)

            # Parse the queue item
            if isinstance(item, tuple):
                if len(item) == 3:
                    text, image, message_id = item
                else:
                    text, image = item
                    message_id = None
            else:
                text = item
                image = None
                message_id = None

            # Generate audio (this is the slow part - ~1s)
            audio = await asyncio.to_thread(_generate_audio, text)

            # Push to playback queue (blocks if player is backed up, which is fine)
            await asyncio.to_thread(
                _playback_queue.put,
                (text, audio, image, message_id)
            )

            tts_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Generator error: %s", e)
            try:
                tts_queue.task_done()
            except ValueError:
                pass

def _play_audio_item(text, audio, image, message_id):
    """Play a single audio item synchronously (runs in the player thread)."""
    global _is_voice_busy, _current_message_id
    _is_voice_busy = True
    _current_message_id = message_id

    try:
        if audio is not None:
            # Calculate audio duration for synchronized text printing
            audio_duration = len(audio) / 24000.0
            delay = (audio_duration - 0.1) / max(len(text), 1)
            if delay < 0.01:
                delay = 0.01

            # Emit to UI with exact duration
            bus.emit(EventType.SPEAK, {
                "text": text,
                "timestamp": time.time(),
                "duration": audio_duration,
                "image": image,
                "message_id": message_id
            })

            # Play the audio
            sd.play(audio, samplerate=24000)
            time.sleep(0.1)  # small delay for audio device wake-up

            # Print synchronized text
            def print_synced():
                for char in text:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    time.sleep(delay)
                print()

            print_thread = threading.Thread(target=print_synced)
            print_thread.start()

            # Wait for audio to finish
            sd.wait()
            print_thread.join()
            
            # Memory Management: Rely on CPython reference counting
            del audio
        else:
            # Fallback: no audio generated (Kokoro failed or text was empty formatting)
            bus.emit(EventType.SPEAK, {
                "text": text,
                "timestamp": time.time(),
                "duration": len(text) * 0.065,
                "image": image,
                "message_id": message_id
            })
            print_animated_message(text)
    except Exception as e:
        logger.error("Playback error: %s", e)
        # Fallback to just printing
        try:
            print_animated_message(text)
        except:
            pass
    finally:
        _current_message_id = None
        _is_voice_busy = False

def _audio_playback_worker() -> None:
    """
    Stage 2: Continuously takes pre-generated audio from _playback_queue
    and plays it. Because the generator is working ahead, the next sentence
    is usually already waiting by the time we finish playing the current one.
    """
    while _is_tts_running:
        try:
            item = _playback_queue.get(timeout=1.0)
            if item is _STREAM_END:
                _playback_queue.task_done()
                continue

            text, audio, image, message_id = item
            _play_audio_item(text, audio, image, message_id)
            _playback_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Player error: %s", e)

def _start_generator_loop():
    """Runs the dedicated TTS generator event loop in a background thread."""
    global _gen_loop
    _gen_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_gen_loop)
    _gen_loop.run_until_complete(_tts_generator_worker())
    _gen_loop.close()

def start_tts_consumer() -> None:
    """Start both background TTS worker threads (generator + player)."""
    global _is_tts_running, _generator_thread, _player_thread
    if not _is_tts_running:
        _is_tts_running = True
        _generator_thread = threading.Thread(target=_start_generator_loop, daemon=True)
        _generator_thread.start()
        _player_thread = threading.Thread(target=_audio_playback_worker, daemon=True)
        _player_thread.start()

def stop_tts_consumer() -> None:
    """Stop the background TTS consumer threads."""
    global _is_tts_running
    _is_tts_running = False

def speak(text: str, image: str = None, message_id: str = None) -> None:
    """
    Unified entry point for Jarvis's voice.
    Always queues text to TTS. Use for conversational content
    (LLM responses, weather, jokes, news, etc.).
    """
    if not _is_tts_running:
        start_tts_consumer()
    tts_queue.put((text, image, message_id))

# Event handler for LLM streaming sentences
def _on_llm_stream(data):
    # data is expected to be a tuple (text, image, message_id)
    if not _is_tts_running:
        start_tts_consumer()
    tts_queue.put(data)

# Register the subscription to bridge llm_manager and mouth decoupling
bus.subscribe(EventType.LLM_STREAMING, _on_llm_stream)

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
    bus.emit(EventType.NOTIFY, {"text": text, "timestamp": time.time()})

def speak_streaming(sentences: list[str]) -> None:
    """Streams a list of sentences to the TTS consumer."""
    if not _is_tts_running:
        start_tts_consumer()
        
    # Clear queue of any previous items to prioritize this stream
    _clear_tts_queue()

    message_id = str(uuid.uuid4())
    for s in sentences:
        if s.strip():
            tts_queue.put((s, None, message_id))

def _clear_tts_queue():
    """Drain the text queue safely."""
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
            tts_queue.task_done()
        except queue.Empty:
            break

def _clear_playback_queue():
    """Drain the playback queue safely."""
    while not _playback_queue.empty():
        try:
            _playback_queue.get_nowait()
            _playback_queue.task_done()
        except queue.Empty:
            break

def wait_for_tts_completion() -> None:
    """Blocks until all queued TTS messages have finished playing."""
    tts_queue.join()
    _playback_queue.join()
    while _is_voice_busy:
        time.sleep(0.1)

def stop_llm_speech() -> None:
    """
    Stop only the streaming speech (LLM responses) without affecting other notifications.
    Clears items with a message_id from both queues and stops audio if currently playing one.
    """
    global _current_message_id
    
    # 1. Filter the text queue: keep items without message_id
    temp_items = []
    while not tts_queue.empty():
        try:
            item = tts_queue.get_nowait()
            if isinstance(item, tuple) and len(item) == 3:
                msg_id = item[2]
                if msg_id is None:
                    temp_items.append(item)
            else:
                temp_items.append(item)
            tts_queue.task_done()
        except queue.Empty:
            break
            
    for item in temp_items:
        tts_queue.put(item)

    # 2. Filter the playback queue: keep items without message_id
    temp_playback = []
    while not _playback_queue.empty():
        try:
            item = _playback_queue.get_nowait()
            if isinstance(item, tuple) and len(item) == 4:
                _, _, _, msg_id = item
                if msg_id is None:
                    temp_playback.append(item)
            else:
                temp_playback.append(item)
            _playback_queue.task_done()
        except queue.Empty:
            break

    for item in temp_playback:
        _playback_queue.put(item)
        
    # 3. If currently playing an LLM response (has message_id), stop audio
    if _current_message_id is not None:
        try:
            sd.stop()
        except Exception as e:
            print(f"Error stopping audio: {e}")
            
    logger.info("Stopped LLM streaming speech.")

if __name__ == "__main__":
    speak("System consolidation complete. I am now using a unified voice module powered by Kokoro.")
    wait_for_tts_completion()
