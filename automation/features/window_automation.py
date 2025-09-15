import os
from head.speak_selector import speak
import pyautogui as ui
import pygetwindow as gw
import time


def handle_minimize():
    """Handle window minimization with improved reliability"""
    speak("Minimizing the window...")
    ui.hotkey("alt", "space")
    time.sleep(0.2)
    ui.press("n")


def handle_maximize():
    """Maximize the current window"""
    speak("Maximizing the window...")
    ui.hotkey("alt", "space")
    time.sleep(0.2)
    ui.press("x")


def handle_restore():
    """Restore window to normal size"""
    speak("Restoring the window...")
    # Use Alt+Space then R to restore (works in English OS)
    ui.hotkey("alt", "space")
    time.sleep(0.2)  # Small delay for menu to appear
    ui.press("r")


def handle_window_switch():
    """Switch between windows"""
    speak("Switching window")
    ui.hotkey("alt", "tab")
    time.sleep(0.5)


def handle_scroll(command_text):
    """Handle scroll commands with adjustable intensity"""
    # Determine scroll direction
    direction = -1 if "down" in command_text else 1

    # Detect intensity from command
    intensity = 1  # Default intensity
    if "little" in command_text or "bit" in command_text:
        intensity = 1
    elif "much" in command_text or "lot" in command_text:
        intensity = 5
    elif "page" in command_text:
        # Use page up/down keys instead of scrolling for larger movements
        if direction == 1:
            ui.press("pageup")
        else:
            ui.press("pagedown")
        speak("Page scrolled")
        return

    # Calculate scroll amount (adjust this value based on your needs)
    scroll_amount = 120 * intensity * direction  # 120 is a typical "click" amount

    # Perform the scroll
    ui.scroll(scroll_amount)

    # Provide feedback
    direction_text = "up" if direction == 1 else "down"
    speak(f"Scrolling {direction_text}")


def handle_scroll_to_top():
    """Scroll to the top of the page"""
    ui.hotkey("ctrl", "home")
    speak("Scrolled to top")


def handle_scroll_to_bottom():
    """Scroll to the bottom of the page"""
    ui.hotkey("ctrl", "end")
    speak("Scrolled to bottom")


def open_incognito_tab():
    """Open an incognito/private browsing window - fixed version"""
    speak("Opening incognito window")

    if activate_browser():
        time.sleep(0.5)

        active_window = gw.getActiveWindow()
        if active_window:
            title = active_window.title.lower()

            if "firefox" in title:
                ui.hotkey("ctrl", "shift", "p")
            else:
                ui.hotkey("ctrl", "shift", "n")
        else:
            ui.hotkey("ctrl", "shift", "n")
    else:
        print("No browser found, opening Chrome in incognito mode")
        os.system("start chrome --incognito")


def bookmark_page():
    """Bookmark the current page"""
    speak("Bookmarking this page")
    ui.hotkey("ctrl", "d")
    time.sleep(0.5)
    ui.hotkey("enter")


def activate_browser():
    """Try to activate a browser window if one exists"""
    try:
        # Get all browser windows
        browsers = ["chrome", "firefox", "edge", "opera", "brave", "safari"]

        all_windows = gw.getAllWindows()

        # Find browser windows
        browser_windows = []
        for window in all_windows:
            if window.title:  # Check if window has a title
                title_lower = window.title.lower()
                if any(keyword in title_lower for keyword in browsers):
                    browser_windows.append(window)

        # Activate the first browser window found
        if browser_windows:
            browser_windows[0].activate()
            time.sleep(0.5)
            return True

        return False
    except Exception as e:
        print(f"Error activating browser: {e}")
        return False


def open_dev_tools():
    """Open developer tools"""
    speak("Opening developer tools")
    ui.hotkey("f12")


def toggle_fullscreen():
    """Toggle fullscreen mode"""
    speak("Toggling fullscreen")
    ui.hotkey("f11")


def reload_page():
    """Reload/refresh the current page"""
    speak("Reloading page")
    ui.hotkey("f5")


def go_back():
    """Go back to previous page"""
    speak("Going back")
    ui.hotkey("alt", "left")


def go_forward():
    """Go forward to next page"""
    speak("Going forward")
    ui.hotkey("alt", "right")


def duplicate_tab():
    """Duplicate the current tab"""
    speak("Duplicating tab")
    ui.hotkey("alt", "d")
    time.sleep(0.1)
    ui.hotkey("alt", "enter")
