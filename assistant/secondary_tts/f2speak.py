"""
F2Speak Module - Fast File-based Text-to-Speech with Animated Display

This module provides a lightweight, efficient text-to-speech system using Microsoft Edge TTS
with file-based audio streaming. It features synchronized animated text display and optimized
memory usage through temporary file management.

Key Features:
- Microsoft Edge TTS integration for high-quality neural voices
- Temporary file streaming for minimal memory footprint
- Synchronized animated text display with audio playback
- Threaded operations for non-blocking user experience
- Pygame-based audio playback with automatic cleanup
- Async/await pattern for efficient resource management

Voice: en-US-JennyNeural (US English, Female Neural Voice)
Audio Format: MP3 via temporary files
Display: Real-time animated text with typewriter effect

Dependencies:
- edge_tts: Microsoft Edge TTS service integration
- pygame: Cross-platform audio playback
- asyncio: Asynchronous operations handling
- threading: Concurrent text animation during audio playback
"""

import asyncio
import os
import edge_tts
import pygame
import tempfile
import threading
import sys
import time

# Voice configuration for TTS - US English, Jenny Neural voice
VOICE = "en-US-JennyNeural"

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()


def print_animated_message(message):
    """
    Display text with typewriter-style animation.

    Creates a dynamic visual experience by printing characters one by one
    with a slight delay, simulating natural reading pace. This enhances
    user engagement during speech synthesis.

    Args:
        message (str): Text to display with animation

    Returns:
        None

    Example:
        Input: "Hello world"
        Output: Characters appear sequentially: H e l l o   w o r l d
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)  # 55ms delay between characters for natural pacing
    print()  # Final newline after message completion


async def stream_audio(text, voice):
    """
    Generate audio file from text using Edge TTS service.

    Converts text to speech asynchronously and saves to a temporary file
    for playback. Uses Microsoft Edge TTS for high-quality neural voice
    synthesis with efficient file-based streaming.

    Args:
        text (str): Text content to convert to speech
        voice (str): Voice identifier for TTS service

    Returns:
        str: Path to the generated temporary audio file

    Raises:
        Exception: If audio generation or file saving fails

    Note:
        Temporary files are automatically created and managed, with
        cleanup handled during audio playback completion.
    """
    communicate = edge_tts.Communicate(text, voice)

    # Create temporary file for audio storage
    # delete=False ensures file persists until explicit cleanup
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Generate and save audio file asynchronously
        await communicate.save(tmp_path)
        return tmp_path
    except Exception as e:
        # Clean up temporary file on error to prevent disk space leaks
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise e


def play_audio_file(file_path):
    """
    Play audio file using Pygame mixer and perform automatic cleanup.

    Loads audio from temporary file, plays it synchronously, and ensures
    file deletion after playback completion to manage disk space efficiently.

    Args:
        file_path (str): Path to audio file for playback

    Returns:
        None

    Workflow:
        1. Load audio file as Pygame Sound object
        2. Start audio playback
        3. Wait for playback completion with non-blocking checks
        4. Delete temporary file regardless of playback success
    """
    try:
        # Load audio file into Pygame Sound object
        sound = pygame.mixer.Sound(file_path)

        # Start audio playback (non-blocking)
        sound.play()

        # Wait for audio playback to complete
        # Check mixer state periodically without blocking system
        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)  # 10 FPS check rate

    except Exception as e:
        print(f"Error playing audio: {e}")
    finally:
        # Always clean up temporary audio file to free disk space
        if os.path.exists(file_path):
            os.unlink(file_path)


async def speak_async(text):
    """
    Asynchronous core function for coordinated TTS and text animation.

    Orchestrates the complete text-to-speech pipeline with synchronized
    visual and audio components. Runs audio generation, text animation,
    and playback in a coordinated manner.

    Args:
        text (str): Text content to speak and display

    Returns:
        None

    Workflow:
        1. Generate audio file asynchronously
        2. Start text animation in separate thread
        3. Play audio file (blocks until completion)
        4. Wait for text animation to complete
    """
    try:
        # Generate audio file from text using Edge TTS
        audio_file_path = await stream_audio(text, VOICE)

        # Create and start a thread for animated text display
        # This runs concurrently with audio processing
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.start()

        # Play audio file in the main thread
        # This blocks until audio playback completes
        play_audio_file(audio_file_path)

        # Wait for the printing thread to finish
        # Ensures text animation completes even if audio finishes first
        print_thread.join()

    except Exception as e:
        print(f"Error in text-to-speech: {e}")


def f2speak(text):
    """
    Main synchronous interface for fast file-based text-to-speech.

    Provides a simple, blocking interface to the async TTS system.
    Wraps the asynchronous functionality in a synchronous call for
    easy integration with existing codebases.

    Args:
        text (str): Text content to speak

    Returns:
        None

    Note:
        This function blocks until both audio playback and text
        animation are complete. For non-blocking operation, consider
        running speak_async directly in an event loop.
    """
    asyncio.run(speak_async(text))


if __name__ == "__main__":
    """
    Main execution block for testing F2Speak functionality.

    Provides a simple test case to verify the TTS system is working
    by speaking a sample phrase. Useful for development and debugging.

    Usage:
        python f2speak.py
    """
    f2speak("hello, how are you?")
