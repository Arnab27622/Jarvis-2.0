"""
Mouth2 Module - Offline Text-to-Speech (TTS) System with Queue-based Streaming

This module provides offline text-to-speech capabilities using pyttsx3, offering
a lightweight, dependency-free alternative to cloud-based TTS services. It features
queue-based streaming for continuous dialogue and synchronized animated text display.

Key Features:
- Offline TTS using pyttsx3 (no internet required)
- Queue-based streaming for continuous speech
- Animated text display synchronized with audio
- Thread-safe operations with locking mechanisms
- Shared TTS engine instance for efficiency
- Configurable speech rate and volume

Advantages over cloud TTS:
- No network latency or dependency
- Consistent performance regardless of internet connectivity
- No API limits or costs
- Faster initialization

Dependencies:
- pyttsx3: Cross-platform offline text-to-speech library
- threading: Concurrent processing for UI and audio
"""

import threading
import time
import sys
import pyttsx3
import queue

# Global queue for TTS sentences - enables streaming multiple sentences
tts_queue = queue.Queue()
_is_tts_running = False  # Control flag for TTS consumer thread
_tts_lock = threading.Lock()  # Thread lock for synchronization
_engine = None  # Shared TTS engine instance for resource efficiency


def print_animated_message(message):
    """
    Print message with character-by-character animation effect.

    Creates a typewriter-like effect by printing each character with a slight delay,
    enhancing user experience during speech synthesis. Slightly slower than cloud version
    to match offline TTS pacing.

    Args:
        message (str): Text to display with animation

    Returns:
        None
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)  # Slightly slower delay for offline TTS compatibility
    print()  # Newline after message completion


def _initialize_engine():
    """
    Initialize and configure the pyttsx3 TTS engine.

    Uses lazy initialization to create the engine only when needed.
    Configures speech rate and volume for optimal offline TTS experience.

    Returns:
        None
    """
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # Configure speech properties
        _engine.setProperty("rate", 180)  # Words per minute (default is 200)
        _engine.setProperty("volume", 1.0)  # Maximum volume (0.0 to 1.0)


def speak(text):
    """
    Main synchronous function for single-sentence offline text-to-speech.

    Provides a simple interface for speaking individual sentences with
    animated text display. Initializes TTS engine on first use.

    Args:
        text (str): Single sentence to speak

    Returns:
        None

    Workflow:
        1. Initialize TTS engine if not already done
        2. Start animated printing in separate thread
        3. Speak text using offline TTS engine
        4. Wait for both audio and display to complete
    """
    global _engine
    _initialize_engine()

    # Start animated printing in separate daemon thread
    print_thread = threading.Thread(target=print_animated_message, args=(text,))
    print_thread.daemon = True  # Thread won't block program exit
    print_thread.start()

    # Speak text and wait for audio completion
    _engine.say(text)
    _engine.runAndWait()  # Blocks until speech finishes

    # Wait for printing thread to complete with timeout
    print_thread.join(timeout=5.0)


def _tts_consumer():
    """
    Background consumer thread for processing TTS queue.

    Continuously monitors the TTS queue and processes sentences
    in sequence. Maintains a single TTS engine instance for
    efficient resource usage across multiple sentences.

    Workflow:
        - Checks queue for new sentences with timeout
        - Processes each sentence through TTS pipeline
        - Handles shutdown signals (None in queue)
        - Manages exceptions gracefully to prevent thread death

    Returns:
        None
    """
    global _is_tts_running, _engine
    _initialize_engine()  # Ensure engine is initialized

    while _is_tts_running or not tts_queue.empty():
        try:
            # Get sentence from queue with 1-second timeout
            sentence = tts_queue.get(timeout=1.0)
            if sentence is None:  # Shutdown signal
                break

            if sentence.strip():  # Only process non-empty sentences
                # Start animated printing thread for current sentence
                print_thread = threading.Thread(
                    target=print_animated_message, args=(sentence,)
                )
                print_thread.daemon = True
                print_thread.start()

                # Speak current sentence (blocks until completion)
                _engine.say(sentence)
                _engine.runAndWait()

                # Wait for printing thread with timeout
                print_thread.join(timeout=5.0)

            tts_queue.task_done()  # Mark task as completed

        except queue.Empty:
            continue  # No sentences available, continue waiting
        except Exception as e:
            print(f"Error in TTS consumer: {e}")
            continue  # Continue processing despite errors


def start_tts_consumer():
    """
    Start the background TTS consumer thread.

    Initializes and starts the consumer thread if not already running.
    Uses thread locking to ensure only one consumer is active.
    Thread is created as daemon to allow clean program exit.

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
    The thread will complete its current task and then exit
    during the next queue check.

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
    Ideal for processing long responses or multiple sentences.

    Args:
        sentences (list): List of sentence strings to speak in sequence

    Returns:
        None

    Note:
        This function clears the existing queue to prevent sentence
        backlog and ensure timely delivery of new content.
    """
    # Clear any existing queue items to avoid backlog
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
            tts_queue.task_done()
        except queue.Empty:
            break

    # Start the consumer thread if not already running
    start_tts_consumer()

    # Add sentences to queue for sequential processing
    for sentence in sentences:
        if sentence.strip():  # Only queue non-empty sentences
            tts_queue.put(sentence)


def wait_for_tts_completion():
    """
    Wait for all queued TTS tasks to complete.

    Blocks until the TTS queue is empty and all audio playback
    has finished. Useful for ensuring complete dialogue delivery
    before proceeding to next operations.

    Returns:
        None
    """
    tts_queue.join()  # Blocks until all tasks are done


if __name__ == "__main__":
    """
    Main execution block for testing offline TTS functionality.

    Provides a simple test case to verify the offline TTS system
    is working by speaking a sample phrase.

    Usage:
        python mouth2.py
    """
    speak("hello, how are you?")
