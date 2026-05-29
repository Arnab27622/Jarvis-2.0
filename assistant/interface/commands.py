"""
Main command module for the Voice Assistant.

This module handles the core command processing logic, including wake word detection,
command mode management, and routing of various voice commands to their respective
functionalities. It serves as the central coordinator for all assistant capabilities.
"""

from assistant.interface.welcome import welcome
from assistant.activities.advice import rand_advice
from assistant.activities.activity_monitor import *
from assistant.core.ear import listen
from assistant.core.brain import brain
from data.dlg_data.dlg import *
from assistant.core.event_bus import text_command_queue
from assistant.core.registry import cmd_registry
import random
import re
import os
import time
import importlib
import pkgutil

FILLER_WORDS = ["please", "can you", "could you", "would you mind", "hey", "jarvis", "tell me", "i want to", "start", "run", "ok", "okay", "alright"]

def normalize_command(text: str) -> str:
    """
    Normalizes the command text by:
    1. Converting to lowercase
    2. Stripping punctuation
    3. Removing wake word 'jarvis'
    4. Removing common filler words
    5. Trimming whitespace
    """
    if not text:
        return ""
    
    # 1. Lowercase
    text = text.lower().strip()
    
    # 2. Strip only "ending" punctuation that doesn't affect internal logic
    # We keep . and : for times/dates, and ' for contractions
    text = re.sub(r'[?,!;]', '', text)
    
    # 3. Remove wake word 'jarvis'
    text = re.sub(r'\bjarvis\b', '', text).strip()
    
    # 4. Remove filler words from start/end (repeatedly until clean)
    changed = True
    while changed:
        changed = False
        for word in FILLER_WORDS:
            new_text = re.sub(rf'^{word}\b', '', text).strip()
            new_text = re.sub(rf'\b{word}$', '', new_text).strip()
            if new_text != text:
                text = new_text
                changed = True
    
    return text


def load_plugins():
    """Dynamically loads all modules in assistant.automation and assistant.activities so commands get registered."""
    import assistant.automation
    import assistant.activities
    
    print("[Registry] Loading plugins...")
    packages = [assistant.automation, assistant.activities]
    for package in packages:
        # Handle packages that don't have __path__
        if not hasattr(package, '__path__'):
            continue
        for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
            try:
                importlib.import_module(module_name)
            except Exception as e:
                pass
                # print(f"Failed to load plugin {module_name}: {e}")
    print("[Registry] Plugins loaded successfully.")

# Load plugins at module level
load_plugins()

def wait_for_wakeword() -> bool:
    """
    Wait for the hotword/wake word to be spoken.
    """
    from assistant.core.speak_selector import speak
    speak("Awaiting your command...")

    while True:
        text = listen()
        if text is None:
            continue

        text_lower = text.lower().strip()

        # Check for confirmation prompt response as well
        if activity_monitor.awaiting_confirmation:
            result = activity_monitor.handle_confirmation_response(text)
            if result is True:
                advice = rand_advice()
                if advice:
                    speak(advice)
                continue
            elif result is False:
                continue
            elif activity_monitor.check_confirmation_timeout():
                activity_monitor.reset_confirmation_state()
                continue

        if any(keyword.strip() == text_lower for keyword in wakeup_key_word):
            activity_monitor.reset_confirmation_state()
            welcome()
            return True

        if any(keyword in text_lower for keyword in bye_key_word):
            response = random.choice(res_bye)
            speak(response)
            stop_activity_monitoring()
            return False


def command() -> None:
    """
    Main command loop managing wake word state and command mode.
    """
    start_activity_monitoring()
    from assistant.core.speak_selector import speak
    command_mode = False

    # Start text command worker thread
    def text_command_worker():
        while True:
            try:
                text = text_command_queue.get()
                print(f"[Debug] text_command_worker got text: {text}")
                if text:
                    record_user_activity()
                    normalized_text = normalize_command(text)
                    print(f"[Debug] normalized: {normalized_text}")
                    if any(keyword.strip() in normalized_text for keyword in stopcmd):
                        speak(random.choice(stopdlg))
                    elif any(keyword.strip() in normalized_text for keyword in cancel_cmd):
                        from assistant.core.mouth import stop_llm_speech
                        stop_llm_speech()
                        speak("Cancelled response.")
                    else:
                        print(f"[Debug] calling process_command")
                        process_command(normalized_text)
                text_command_queue.task_done()
            except Exception as e:
                print(f"Error in text worker: {e}")

    threading.Thread(target=text_command_worker, daemon=True).start()

    while True:
        text = listen(emit_to_ui=command_mode)
        if text is None:
            print("Sorry, I couldn't understand. Please try again.")
            continue

        text_lower = text.lower().strip()

        if activity_monitor.awaiting_confirmation:
            result = activity_monitor.handle_confirmation_response(text)
            if result is True:
                advice = rand_advice()
                if advice:
                    speak(advice)
                continue
            elif result is False:
                continue
            elif activity_monitor.check_confirmation_timeout():
                activity_monitor.reset_confirmation_state()

        if any(keyword in text_lower for keyword in bye_key_word):
            response = random.choice(res_bye)
            speak(response)
            stop_activity_monitoring()
            break

        if not command_mode:
            if any(keyword.strip() == text_lower for keyword in wakeup_key_word):
                activity_monitor.reset_confirmation_state()
                welcome()
                command_mode = True
            continue

        record_user_activity()
        normalized_text = normalize_command(text_lower)

        if any(keyword.strip() in normalized_text for keyword in stopcmd):
            speak(random.choice(stopdlg))
            command_mode = False
            continue

        if any(keyword.strip() in normalized_text for keyword in cancel_cmd):
            from assistant.core.mouth import stop_llm_speech
            stop_llm_speech()
            speak("Cancelled response.")
            continue

        try:
            process_command(normalized_text)
        except Exception as e:
            print(f"Error in command execution: {e}")
            speak("I encountered an internal problem while executing that command.")


def process_command(normalized_text: str) -> None:
    """
    Process and execute voice commands using a modular registry system.
    """
    start_time = time.time()
    from assistant.core.speak_selector import speak
    import threading
    
    try:
        background_task_started = False
        if not normalized_text:
            from assistant.interface.welcome import welcome
            welcome()
            return

        # Emit PROCESSING event
        from assistant.core.event_bus import bus, EventType
        bus.emit(EventType.PROCESSING, {"state": True})

        # Attempt to execute command from registry
        if not cmd_registry.execute(normalized_text):
            # Fallback to AI brain for unrecognized commands
            # Run in a background thread to prevent blocking the main listening loop
            background_task_started = True
            threading.Thread(target=brain, args=(normalized_text,), daemon=True).start()
    except Exception as e:
        print(f"Error in process_command: {e}")
        speak("I had trouble understanding or executing that command.")
    finally:
        from assistant.core.ear import recognizer
        actual_start = getattr(recognizer, 'last_recognition_time', start_time)
        execution_time = time.time() - actual_start
        print(f"[Timer] Command executed in {execution_time:.2f} seconds.")
        # Reset to avoid reusing the same timestamp for subsequent immediate calls
        recognizer.last_recognition_time = time.time()
        
        if not background_task_started:
            bus.emit(EventType.COMMAND_EXECUTED, {})

if __name__ == "__main__":
    pass
