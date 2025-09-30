"""
Mouth Module - Text-to-Speech (TTS) System with Queue-based Streaming

This module provides advanced text-to-speech capabilities using Edge TTS and Pygame
for audio playback. It supports both single-sentence speaking and queue-based streaming
for continuous dialogue with animated text display.

Key Features:
- Asynchronous TTS generation using Microsoft Edge TTS
- Queue-based streaming for continuous speech
- Animated text display synchronized with audio
- Thread-safe operations with locking mechanisms
- Temporary file management for audio streaming
- Support for multiple sentences in sequence

Dependencies:
- edge_tts: Microsoft Edge TTS service integration
- pygame: Audio playback and mixing
- asyncio: Asynchronous operations handling
- threading: Concurrent processing for UI and audio
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

# Voice configuration for TTS - Australian English, William Neural voice
VOICE = "en-AU-WilliamNeural"

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()

# Global queue for TTS sentences - enables streaming multiple sentences
tts_queue = queue.Queue()
_is_tts_running = False  # Control flag for TTS consumer thread
_tts_lock = threading.Lock()  # Thread lock for synchronization


def print_animated_message(message):
    """
    Print message with character-by-character animation effect.

    Creates a typewriter-like effect by printing each character with a slight delay,
    enhancing user experience during speech synthesis.

    Args:
        message (str): Text to display with animation

    Returns:
        None
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)  # Delay between characters for natural reading pace
    print()  # Newline after message completion


async def stream_audio(text, voice):
    """
    Generate audio file from text using Edge TTS service.

    Converts text to speech asynchronously and saves to a temporary file
    for playback. Uses Microsoft Edge TTS for high-quality neural voice synthesis.

    Args:
        text (str): Text content to convert to speech
        voice (str): Voice identifier for TTS service

    Returns:
        str: Path to the generated temporary audio file

    Raises:
        Exception: If audio generation or file saving fails
    """
    communicate = edge_tts.Communicate(text, voice)

    # Create temporary file for audio storage
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Generate and save audio file
        await communicate.save(tmp_path)
        return tmp_path
    except Exception as e:
        # Clean up temporary file on error
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise e


def play_audio_file(file_path):
    """
    Play audio file using Pygame mixer and clean up afterward.

    Loads audio file, plays it synchronously, and deletes the temporary file
    after playback completion to manage disk space.

    Args:
        file_path (str): Path to audio file for playback

    Returns:
        None
    """
    try:
        # Load and play audio file
        sound = pygame.mixer.Sound(file_path)
        sound.play()

        # Wait for audio playback to complete
        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)  # 10 FPS check for playback status

    except Exception as e:
        print(f"Error playing audio: {e}")
    finally:
        # Always clean up temporary audio file
        if os.path.exists(file_path):
            os.unlink(file_path)


async def _speak_async(text):
    """
    Asynchronous core function for text-to-speech processing.

    Coordinates the complete TTS pipeline:
    - Audio file generation
    - Animated text display in separate thread
    - Synchronized audio playback

    Args:
        text (str): Text content to speak and display

    Returns:
        None
    """
    try:
        # Generate audio file from text
        audio_file_path = await stream_audio(text, VOICE)

        # Create and start a thread for animated printing
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.start()

        # Play audio in the main thread (blocks until completion)
        play_audio_file(audio_file_path)

        # Wait for the printing thread to finish
        print_thread.join()

    except Exception as e:
        print(f"Error in text-to-speech: {e}")


def speak(text):
    """
    Main synchronous function for single-sentence text-to-speech.

    Provides a thread-safe interface for speaking individual sentences.
    Uses locking to prevent overlapping TTS operations.

    Args:
        text (str): Single sentence to speak

    Returns:
        None
    """
    with _tts_lock:
        time.sleep(0.1)  # Brief delay for system stability
        asyncio.run(_speak_async(text))


def _tts_consumer():
    """
    Background consumer thread for processing TTS queue.

    Continuously monitors the TTS queue and processes sentences
    in sequence. Runs as long as the system is active or until
    queue is empty.

    Workflow:
        - Checks queue for new sentences
        - Processes each sentence through TTS pipeline
        - Handles shutdown signals
        - Manages exceptions gracefully

    Returns:
        None
    """
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
            continue  # No sentences available, continue waiting
        except Exception as e:
            print(f"Error in TTS consumer: {e}")
            continue


def start_tts_consumer():
    """
    Start the background TTS consumer thread.

    Initializes and starts the consumer thread if not already running.
    Uses thread locking to ensure only one consumer is active.

    Returns:
        None
    """
    global _is_tts_running
    with _tts_lock:
        if not _is_tts_running:
            _is_tts_running = True
            # Create daemon thread that won't block program exit
            consumer_thread = threading.Thread(target=_tts_consumer, daemon=True)
            consumer_thread.start()


def stop_tts_consumer():
    """
    Stop the background TTS consumer thread.

    Signals the consumer thread to stop processing and exit.
    Does not force immediate termination - completes current task.

    Returns:
        None
    """
    global _is_tts_running
    with _tts_lock:
        _is_tts_running = False


def speak_streaming(sentences):
    """
    Stream multiple sentences to TTS queue for sequential playback.

    Clears any existing queue backlog and streams new sentences
    for continuous dialogue. Starts consumer thread if not running.

    Args:
        sentences (list): List of sentence strings to speak in sequence

    Returns:
        None
    """
    # Clear any existing queue items to avoid backlog
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
            tts_queue.task_done()
        except queue.Empty:
            break

    # Start the consumer if not running
    start_tts_consumer()

    # Add sentences to queue for processing
    for sentence in sentences:
        if sentence.strip():  # Only queue non-empty sentences
            tts_queue.put(sentence)


def wait_for_tts_completion():
    """
    Wait for all queued TTS tasks to complete.

    Blocks until the TTS queue is empty and all audio playback
    has finished. Useful for ensuring complete dialogue delivery.

    Returns:
        None
    """
    tts_queue.join()


if __name__ == "__main__":
    """
    Main execution block for testing TTS functionality.

    Provides a simple test case to verify the TTS system is working
    by speaking a sample phrase.

    Usage:
        python mouth.py
    """
    speak("hello, how are you?")
