"""
Mouth Module - Unified Text-to-Speech (TTS) System

Now powered by Kokoro TTS for ultra-low latency streaming.
"""

import sys
import time
import threading
import queue
import sounddevice as sd
from kokoro_onnx import Kokoro
import asyncio

# --- New Kokoro Implementation ---

# Global state
_tts_lock = threading.Lock()
tts_queue = queue.Queue()
_is_tts_running = False

# Initialize Kokoro
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


def print_animated_message(message: str) -> None:
    """
    Print a message to the console character by character for a typing effect.

    Args:
        message (str): The text to print.
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)
    print()


async def _stream_audio_and_text(text: str) -> None:
    """
    Generate audio stream using Kokoro TTS and synchronize it with console text printing.

    Args:
        text (str): The text to synthesize into speech.
    """
    if not kokoro_ready:
        print_animated_message(text)
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
                # Play the chunk first, which initializes the audio device (can take 0.2-0.5s)
                sd.play(chunk, samplerate=24000)
                time.sleep(0.3) # Give audio device time to actually start outputting sound
                # Now start printing so it matches the sound
                print_thread.start()
                first_chunk = False
                sd.wait()
            else:
                # play chunk blocking so they queue up properly
                sd.play(chunk, samplerate=24000)
                sd.wait()

        # Fallback if no audio was generated for some reason
        if first_chunk:
            print_thread.start()

        print_thread.join()
    except Exception as e:
        print(f"Kokoro Streaming Error: {e}")
        # fallback to just printing if playback fails
        print_animated_message(text)


def speak(text: str) -> None:
    """
    Unified entry point for Jarvis's voice.
    Uses Kokoro TTS for real-time streaming.
    """
    with _tts_lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If an event loop is already running, run the coroutine in a new thread and wait for it
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_stream_audio_and_text(text))
                new_loop.close()

            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()
        else:
            asyncio.run(_stream_audio_and_text(text))


def speak_streaming(sentences: list[str]) -> None:
    """Streams a list of sentences to the TTS consumer."""
    global _is_tts_running
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
            tts_queue.task_done()
        except:
            break

    if not _is_tts_running:
        _is_tts_running = True
        threading.Thread(target=_tts_consumer, daemon=True).start()

    for s in sentences:
        if s.strip():
            tts_queue.put(s)


def _tts_consumer() -> None:
    """Background worker that continuously consumes from the TTS queue."""
    global _is_tts_running
    while _is_tts_running:
        try:
            sentence = tts_queue.get(timeout=2.0)
            speak(sentence)
            tts_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Streaming error: {e}")


def wait_for_tts_completion() -> None:
    """Block until all sentences in the TTS queue have been spoken."""
    tts_queue.join()


def start_tts_consumer() -> None:
    """Start the background TTS consumer thread."""
    global _is_tts_running
    _is_tts_running = True
    threading.Thread(target=_tts_consumer, daemon=True).start()


def stop_tts_consumer() -> None:
    """Stop the background TTS consumer thread."""
    global _is_tts_running
    _is_tts_running = False




# =====================================================================
# Old TTS Implementation
# =====================================================================
'''
import asyncio
import os
import edge_tts
import pygame
import tempfile
import sys
import time
import threading
import queue
import pyttsx3
import random
from textblob import TextBlob
from assistant.activities.check_status import is_online

# Voice configurations
ONLINE_VOICE = "en-AU-WilliamNeural"  # High quality Australian voice
OFFLINE_VOICE_INDEX = 1               # Typically female voice for pyttsx3

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()

# Global state for synchronized operations
_tts_lock = threading.Lock()
tts_queue = queue.Queue()
_is_tts_running = False

# --- Emotion Analysis Logic ---

def get_emotional_params(text):
    """
    Analyze text sentiment and return suggested speech rate and volume.
    Used for offline TTS to make it sound more natural.
    """
    try:
        sentiment = TextBlob(text).sentiment.polarity
        if sentiment > 0.7: return 220, 1.5   # Ecstatic
        elif sentiment > 0.3: return 170, 1.1  # Happy
        elif sentiment > -0.1: return 150, 1.0 # Neutral
        elif sentiment > -0.5: return 110, 1.0 # Sad
        else: return 100, 0.8                  # Distressed
    except:
        return 150, 1.0 # Default fallback

# --- Offline Engine Logic ---

def _offline_speak(text):
    """
    Executes offline TTS using pyttsx3 with dynamic emotion adjustment.
    """
    try:
        engine = pyttsx3.init()
        rate, volume = get_emotional_params(text)
        
        voices = engine.getProperty("voices")
        if len(voices) > OFFLINE_VOICE_INDEX:
            engine.setProperty("voice", voices[OFFLINE_VOICE_INDEX].id)
            
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        
        # Start animated printing in a thread
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.start()
        
        engine.say(text)
        engine.runAndWait()
        print_thread.join()
    except Exception as e:
        print(f"Offline TTS Error: {e}")
        # Final fallback: just print the message
        print_animated_message(text)

# --- Online Engine Logic ---

async def _generate_online_audio(text):
    communicate = edge_tts.Communicate(text, ONLINE_VOICE)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

def _play_audio_file(file_path):
    try:
        sound = pygame.mixer.Sound(file_path)
        sound.play()
        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)

async def _online_speak_async(text):
    try:
        audio_path = await _generate_online_audio(text)
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.start()
        _play_audio_file(audio_path)
        print_thread.join()
    except Exception as e:
        print(f"Online TTS Error: {e}. Falling back to offline...")
        _offline_speak(text)

# --- Core Printing Logic ---

def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)
    print()

# --- Public API ---

def speak(text):
    """
    Unified entry point for Jarvis's voice. 
    Automatically selects Online High-Quality vs Offline Emotion-Aware TTS.
    """
    with _tts_lock:
        if is_online():
            asyncio.run(_online_speak_async(text))
        else:
            _offline_speak(text)

def speak_streaming(sentences):
    """Streams a list of sentences to the TTS consumer."""
    global _is_tts_running
    # Clear queue
    while not tts_queue.empty():
        try: 
            tts_queue.get_nowait()
            tts_queue.task_done()
        except: 
            break
    
    # Start consumer if needed
    if not _is_tts_running:
        _is_tts_running = True
        threading.Thread(target=_tts_consumer, daemon=True).start()
        
    for s in sentences:
        if s.strip(): 
            tts_queue.put(s)

def _tts_consumer():
    global _is_tts_running
    while _is_tts_running:
        try:
            sentence = tts_queue.get(timeout=2.0)
            speak(sentence)
            tts_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Streaming error: {e}")

def wait_for_tts_completion():
    tts_queue.join()

def start_tts_consumer():
    global _is_tts_running
    _is_tts_running = True
    threading.Thread(target=_tts_consumer, daemon=True).start()

def stop_tts_consumer():
    global _is_tts_running
    _is_tts_running = False

if __name__ == "__main__":
    speak("System consolidation complete. I am now using a unified voice module.")
'''

if __name__ == "__main__":
    speak(
        "System consolidation complete. I am now using a unified voice module powered by Kokoro."
    )
