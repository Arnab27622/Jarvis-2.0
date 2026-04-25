"""
Mouth Module - Unified Text-to-Speech (TTS) System

Consolidates online (Edge TTS) and offline (pyttsx3) capabilities into a 
single module. Features intelligent online/offline fallback and 
emotion-aware offline speech synthesis.
"""

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

