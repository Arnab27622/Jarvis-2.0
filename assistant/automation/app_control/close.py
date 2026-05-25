import pyautogui as ui
import random
import psutil
from assistant.core.speak_selector import speak
from data.dlg_data.dlg import closedlg


from typing import Optional

def close_command(app_name: Optional[str] = None) -> None:
    """
    Close the currently active application or window.

    This function performs a system-level close operation by:
    1. Providing voice feedback using a randomly selected closing message
    2. Sending the Alt+F4 keyboard shortcut to close the active window

    The Alt+F4 shortcut is the standard Windows keyboard command for
    closing the currently focused application, similar to clicking the
    X button in the window title bar.

    Note:
        This will close whatever application currently has focus, so use
        with caution when important unsaved work might be open.

    Example:
        >>> close_command()
        # Speaks: "Closing the application now" (random choice)
        # Sends: Alt+F4 keyboard shortcut

    Dependencies:
        - pyautogui: For sending system keyboard shortcuts
        - speak: For voice feedback to the user
        - closedlg: For random closing dialogue messages
    """
    if app_name:
        speak(f"Closing {app_name}")
        app_name_lower = app_name.lower()
        killed = False
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and app_name_lower in name.lower():
                    proc.kill()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        if not killed:
            speak(f"I couldn't find {app_name} running.")
    else:
        speak(random.choice(closedlg))
        ui.hotkey("alt", "f4")
