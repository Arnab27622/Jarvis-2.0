import threading
import time
import sys
import pyttsx3

_speak_lock = threading.Lock()
_engine = None  # Shared TTS engine instance


def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.065)
    print()


def speak(text):
    """Speak text with offline TTS with animated printing"""
    global _engine

    with _speak_lock:
        if _engine is None:
            _engine = pyttsx3.init()
            _engine.setProperty("rate", 180)
            _engine.setProperty("volume", 1.0)

        # Start animated printing thread
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.daemon = True  # Make thread daemon to avoid blocking on join
        print_thread.start()

        # Speak and wait for completion
        _engine.say(text)
        _engine.runAndWait()

        # Wait for printing thread (with timeout to prevent deadlocks)
        print_thread.join(timeout=5.0)


if __name__ == "__main__":
    speak("hello, how are you?")
