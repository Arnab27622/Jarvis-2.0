# mouth.py (modified for queue-based streaming)
import asyncio
import os
import edge_tts
import pygame
import tempfile
import sys
import time
import threading
import queue
import re

VOICE = "en-AU-WilliamNeural"

pygame.init()
pygame.mixer.init()

# Global queue for TTS sentences
tts_queue = queue.Queue()
_is_tts_running = False
_tts_lock = threading.Lock()


def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.055)
    print()


async def stream_audio(text, voice):
    """Stream audio directly without storing the entire file in memory"""
    communicate = edge_tts.Communicate(text, voice)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name

    try:
        await communicate.save(tmp_path)
        return tmp_path
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise e


def play_audio_file(file_path):
    """Play audio from file and then clean up"""
    try:
        sound = pygame.mixer.Sound(file_path)
        sound.play()

        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Error playing audio: {e}")
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)


async def _speak_async(text):
    """Async function to generate and play audio"""
    try:
        # Generate audio file first
        audio_file_path = await stream_audio(text, VOICE)

        # Create and start a thread for animated printing
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.start()

        # Play audio in the main thread
        play_audio_file(audio_file_path)

        # Wait for the printing thread to finish
        print_thread.join()

    except Exception as e:
        print(f"Error in text-to-speech: {e}")


def speak(text):
    """Main function to speak text (for single sentences)"""
    with _tts_lock:
        time.sleep(0.1)
        asyncio.run(_speak_async(text))


def _tts_consumer():
    """Background thread that consumes sentences from the queue and speaks them"""
    global _is_tts_running

    while _is_tts_running or not tts_queue.empty():
        try:
            # Get sentence from queue with timeout
            sentence = tts_queue.get(timeout=1.0)
            if sentence is None:  # Shutdown signal
                break

            if sentence.strip():  # Only speak non-empty sentences
                asyncio.run(_speak_async(sentence))

            tts_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in TTS consumer: {e}")
            continue


def start_tts_consumer():
    """Start the TTS consumer thread"""
    global _is_tts_running
    with _tts_lock:
        if not _is_tts_running:
            _is_tts_running = True
            consumer_thread = threading.Thread(target=_tts_consumer, daemon=True)
            consumer_thread.start()


def stop_tts_consumer():
    """Stop the TTS consumer thread"""
    global _is_tts_running
    with _tts_lock:
        _is_tts_running = False


def speak_streaming(sentences):
    """Stream sentences to the TTS queue"""
    # Clear any existing queue items to avoid backlog
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
            tts_queue.task_done()
        except queue.Empty:
            break

    # Start the consumer if not running
    start_tts_consumer()

    # Add sentences to queue
    for sentence in sentences:
        if sentence.strip():  # Only queue non-empty sentences
            tts_queue.put(sentence)


def wait_for_tts_completion():
    """Wait for all queued TTS tasks to complete"""
    tts_queue.join()


if __name__ == "__main__":
    speak("hello, how are you?")
