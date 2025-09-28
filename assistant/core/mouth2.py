# mouth2.py (modified for queue-based streaming)
import threading
import time
import sys
import pyttsx3
import queue

# Global queue for TTS sentences
tts_queue = queue.Queue()
_is_tts_running = False
_tts_lock = threading.Lock()
_engine = None  # Shared TTS engine instance


def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)
    print()


def _initialize_engine():
    """Initialize the TTS engine"""
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 180)
        _engine.setProperty("volume", 1.0)


def speak(text):
    """Speak text with offline TTS (for single sentences)"""
    global _engine
    _initialize_engine()

    # Start animated printing thread
    print_thread = threading.Thread(target=print_animated_message, args=(text,))
    print_thread.daemon = True
    print_thread.start()

    # Speak and wait for completion
    _engine.say(text)
    _engine.runAndWait()

    # Wait for printing thread
    print_thread.join(timeout=5.0)


def _tts_consumer():
    """Background thread that consumes sentences from the queue and speaks them"""
    global _is_tts_running, _engine
    _initialize_engine()

    while _is_tts_running or not tts_queue.empty():
        try:
            # Get sentence from queue with timeout
            sentence = tts_queue.get(timeout=1.0)
            if sentence is None:  # Shutdown signal
                break

            if sentence.strip():  # Only speak non-empty sentences
                # Start animated printing thread for this sentence
                print_thread = threading.Thread(
                    target=print_animated_message, args=(sentence,)
                )
                print_thread.daemon = True
                print_thread.start()

                # Speak this sentence
                _engine.say(sentence)
                _engine.runAndWait()

                # Wait for printing thread
                print_thread.join(timeout=5.0)

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
