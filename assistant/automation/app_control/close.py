import pyautogui as ui
import random
from assistant.core.speak_selector import speak
from data.dlg_data.dlg import closedlg


def close_command():
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
    speak(random.choice(closedlg))
    ui.hotkey("alt", "f4")
