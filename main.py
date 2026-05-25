"""
Main entry point for the Jarvis 2.0 Assistant.

This module initializes the core systems, restores any active background tasks
such as alarms and reminders, starts system monitors, and enters the main
command listening loop.
"""

import random

from assistant.interface.wish import wish
from assistant.interface.commands import command
from data.dlg_data.dlg import offline_dlg, online_dlg
from assistant.activities.check_status import is_online
from assistant.core.speak_selector import speak
from assistant.activities.activity_monitor import stop_activity_monitoring
from assistant.activities.battery_features import battery_monitor






def jarvis() -> None:
    """
    Initialize and run the core Jarvis loop.

    This function triggers the initial greeting, starts the battery monitor,
    and enters the main command execution loop.
    """
    from assistant.core.mouth import wait_for_tts_completion
    wish()
    battery_monitor.start_monitoring()
    wait_for_tts_completion()
    command()


if __name__ == "__main__":
    try:
        if is_online():
            speak(random.choice(online_dlg))
            speak("Initializing JARVIS...")
            jarvis()
        else:
            speak(random.choice(offline_dlg))
    except KeyboardInterrupt:
        stop_activity_monitoring()
        battery_monitor.stop_monitoring()
        print("\nJARVIS shutting down...")
    except Exception as e:
        stop_activity_monitoring()
        battery_monitor.stop_monitoring()
        print(f"An error occurred: {e}")
        print("JARVIS shutting down due to error...")
    finally:
        from assistant.core.mouth import wait_for_tts_completion, stop_tts_consumer
        wait_for_tts_completion()
        stop_tts_consumer()