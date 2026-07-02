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
import sys
import tempfile

from assistant.interface.wish import wish
from assistant.interface.commands import command
from data.dlg_data.dlg import offline_dlg
from assistant.activities.check_status import is_online
from assistant.core.speak_selector import speak
from assistant.activities.activity_monitor import stop_activity_monitoring
from assistant.activities.battery_features import battery_monitor






def jarvis() -> None:
    """
    Initialize and run the core Jarvis loop.

    This function triggers the initial greeting and enters the main command execution loop.
    """
    from assistant.core.mouth import wait_for_tts_completion
    wish()
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
            # Early Monitor Initialization
            battery_monitor.start_monitoring()

            # Start background pre-warming of heavy ML models
            def prewarm_models():
                try:
                    pass
                except Exception as e:
                    import logging
                    logging.getLogger("Main").error(f"Failed to prewarm models: {e}")
            threading.Thread(target=prewarm_models, daemon=True).start()

            # Start Web UI Server in background thread FIRST so event bus is ready
            from assistant.web.server import start_web_server, manager
            web_thread = threading.Thread(target=start_web_server, args=(1410,), daemon=True)
            web_thread.start()
            
            # Poll until port is bound (max 5s) to replace time.sleep(0.5)
            import socket
            start_poll = time.time()
            server_ready = False
            while time.time() - start_poll < 5.0:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(('127.0.0.1', 1410)) == 0:
                        server_ready = True
                        break
                time.sleep(0.1)
                
            if not server_ready:
                print("\nCRITICAL ERROR: Failed to start Web UI server on port 1410.")
                sys.exit(1)
            
            # Open browser window exactly BEFORE auth starts so the user sees the SVG loading screen
            browser_proc = launch_browser()
            
            # Poll until UI connects to WebSocket (max 10s) to replace time.sleep(4)
            start_poll = time.time()
            ui_ready = False
            while time.time() - start_poll < 10.0:
                if manager.active_connections:
                    ui_ready = True
                    break
                time.sleep(0.1)
                
            if not ui_ready:
                print("\nCRITICAL ERROR: Web UI failed to connect via WebSocket.")
                if browser_proc:
                    try:
                        browser_proc.terminate()
                    except Exception:
                        pass
                sys.exit(1)
            
            # Run Face Authentication
            from assistant.core.auth import authenticate_user
            if not authenticate_user():
                print("\nAuthentication failed or aborted. Exiting JARVIS.")
                if browser_proc:
                    try:
                        browser_proc.terminate()
                    except Exception:
                        pass
                sys.exit(0)
            
            # Wait for JARVIS to actually finish speaking/printing the lines
            from assistant.core.mouth import wait_for_tts_completion
            wait_for_tts_completion()
            
            # Start proactive manager after successful authentication
            from assistant.core.proactive import proactive_manager
            proactive_manager.start()
            
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
        from assistant.core.proactive import proactive_manager
        proactive_manager.stop()
        from assistant.core.mouth import wait_for_tts_completion, stop_tts_consumer
        wait_for_tts_completion()
        stop_tts_consumer()