"""
Main entry point for the Jarvis 2.0 Assistant.

This module initializes the core systems, restores any active background tasks
such as alarms and reminders, starts system monitors, and enters the main
command listening loop.
"""

import random
import threading
import time
import subprocess
import os
import tempfile

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
    from assistant.core.proactive import proactive_manager
    wish()
    battery_monitor.start_monitoring()
    proactive_manager.start()
    wait_for_tts_completion()
    command()


def launch_browser() -> subprocess.Popen:
    """Launch an isolated app-mode browser window that can be killed later."""
    url = "http://localhost:1410"
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    # Use a temporary profile to force a new, isolated process that doesn't merge with existing tabs
    user_data_dir = os.path.join(tempfile.gettempdir(), "jarvis_browser_profile")
    
    if os.path.exists(chrome_path):
        cmd = [chrome_path, f"--app={url}", f"--user-data-dir={user_data_dir}"]
    elif os.path.exists(edge_path):
        cmd = [edge_path, f"--app={url}", f"--user-data-dir={user_data_dir}"]
    else:
        # Fallback to default browser if neither is found
        import webbrowser
        webbrowser.open(url)
        return None
        
    return subprocess.Popen(cmd)


if __name__ == "__main__":
    browser_proc = None
    try:
        if is_online():
            # Start Web UI Server in background thread FIRST so event bus is ready
            from assistant.web.server import start_web_server
            web_thread = threading.Thread(target=start_web_server, args=(1410,), daemon=True)
            web_thread.start()
            time.sleep(0.5)
            
            # Queue the startup greetings
            speak(random.choice(online_dlg))
            speak("Initializing JARVIS...")
            
            # Wait for JARVIS to actually finish speaking/printing the lines
            from assistant.core.mouth import wait_for_tts_completion
            wait_for_tts_completion()
            
            # Open browser window exactly AFTER it finishes saying the lines
            browser_proc = launch_browser()
            
            jarvis()
        else:
            speak(random.choice(offline_dlg))
    except KeyboardInterrupt:
        stop_activity_monitoring()
        battery_monitor.stop_monitoring()
        from assistant.core.proactive import proactive_manager
        proactive_manager.stop()
        print("\nJARVIS shutting down...")
    except Exception as e:
        stop_activity_monitoring()
        battery_monitor.stop_monitoring()
        from assistant.core.proactive import proactive_manager
        proactive_manager.stop()
        print(f"An error occurred: {e}")
        print("JARVIS shutting down due to error...")
    finally:
        # Ensure we kill the browser when JARVIS shuts down
        if browser_proc:
            try:
                browser_proc.terminate()
            except Exception:
                pass
        from assistant.core.mouth import wait_for_tts_completion, stop_tts_consumer
        wait_for_tts_completion()
        stop_tts_consumer()