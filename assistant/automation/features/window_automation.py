import os
from assistant.core.speak_selector import speak
import pyautogui as ui
import pygetwindow as gw
import time


def handle_minimize():
    """
    Minimize the currently active window using system keyboard shortcuts.

    Uses the Windows system menu (Alt+Space) followed by the minimize command (N)
    to reliably minimize the foreground window regardless of application type.

    Process:
        1. Opens window system menu with Alt+Space
        2. Sends 'N' key to select minimize option
        3. Provides voice confirmation

    Note:
        This method works across most Windows applications and is more reliable
        than application-specific minimize methods.
    """
    speak("Minimizing the window...")
    ui.hotkey("alt", "space")
    time.sleep(0.2)
    ui.press("n")


def handle_maximize():
    """
    Maximize the currently active window to full screen.

    Uses the Windows system menu (Alt+Space) followed by the maximize command (X)
    to expand the window to fill the entire screen.

    Process:
        1. Opens window system menu with Alt+Space
        2. Sends 'X' key to select maximize option
        3. Provides voice confirmation

    Note:
        Works consistently across different Windows applications and window types.
    """
    speak("Maximizing the window...")
    ui.hotkey("alt", "space")
    time.sleep(0.2)
    ui.press("x")


def handle_restore():
    """
    Restore a window from minimized or maximized state to normal size.

    Uses the Windows system menu (Alt+Space) followed by the restore command (R)
    to return the window to its previous non-maximized, non-minimized state.

    Process:
        1. Opens window system menu with Alt+Space
        2. Sends 'R' key to select restore option
        3. Provides voice confirmation

    Note:
        This command assumes English OS language settings. The restore hotkey
        may differ for non-English Windows installations.
    """
    speak("Restoring the window...")
    # Use Alt+Space then R to restore (works in English OS)
    ui.hotkey("alt", "space")
    time.sleep(0.2)  # Small delay for menu to appear
    ui.press("r")


def handle_window_switch():
    """
    Switch between open windows using Alt+Tab task switcher.

    Activates the Windows task switcher interface allowing the user to
    cycle through open applications. The switcher remains open briefly
    for the user to make a selection.

    Process:
        1. Activates Alt+Tab task switcher
        2. Maintains switcher open for 0.5 seconds
        3. User can continue holding Alt to browse or release to select

    Note:
        The function doesn't complete the window switch - it only opens
        the switcher. User must complete the selection.
    """
    speak("Switching window")
    ui.hotkey("alt", "tab")
    time.sleep(0.5)


def handle_scroll(command_text):
    """
    Handle scroll commands with intelligent direction and intensity detection.

    Analyzes voice commands to determine scroll direction and amount,
    supporting both mouse wheel scrolling and page-based navigation.

    Args:
        command_text (str): Voice command containing scroll instructions.
                          Examples: "scroll down", "scroll up a little",
                          "scroll down a lot", "scroll page down"

    Scroll Types:
        - Mouse wheel scrolling: For precise, small movements
        - Page scrolling: For larger document navigation

    Intensity Levels:
        - "little" or "bit": 1x scroll (120 units)
        - Default: 1x scroll (120 units)
        - "much" or "lot": 5x scroll (600 units)
        - "page": Uses Page Up/Down keys for full page navigation

    Note:
        Scroll amount of 120 units represents one typical mouse wheel "click".
    """
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
    """
    Scroll to the top of the current document or page.

    Uses Ctrl+Home keyboard shortcut which works in most applications
    including web browsers, document editors, and file explorers.
    """
    ui.hotkey("ctrl", "home")
    speak("Scrolled to top")


def handle_scroll_to_bottom():
    """
    Scroll to the bottom of the current document or page.

    Uses Ctrl+End keyboard shortcut which works in most applications
    including web browsers, document editors, and file explorers.
    """
    ui.hotkey("ctrl", "end")
    speak("Scrolled to bottom")


def open_incognito_tab():
    """
    Open a private browsing window in the active browser.

    Detects the currently active browser and uses the appropriate
    keyboard shortcut to open a private browsing session. Falls back
    to opening Chrome in incognito mode if no browser is active.

    Browser Support:
        - Firefox: Ctrl+Shift+P
        - Chrome/Edge/Opera/Brave: Ctrl+Shift+N
        - Safari: Not specifically handled (uses default)

    Process:
        1. Attempts to activate an existing browser window
        2. Detects browser type from window title
        3. Uses browser-specific private browsing shortcut
        4. Falls back to launching Chrome if no browser found
    """
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
    """
    Bookmark the current web page using browser keyboard shortcuts.

    Uses Ctrl+D to open the bookmark dialog and then presses Enter
    to confirm, creating a bookmark with the default name and location.

    Process:
        1. Opens bookmark dialog with Ctrl+D
        2. Confirms with Enter after brief delay
        3. Provides voice confirmation

    Compatibility:
        Works with most modern browsers including Chrome, Firefox, Edge, etc.
    """
    speak("Bookmarking this page")
    ui.hotkey("ctrl", "d")
    time.sleep(0.5)
    ui.hotkey("enter")


def activate_browser():
    """
    Find and activate an existing browser window if available.

    Searches through all open windows to find browser applications
    and activates the first one found. Supports multiple browser types.

    Returns:
        bool: True if a browser window was found and activated, False otherwise

    Supported Browsers:
        Chrome, Firefox, Edge, Opera, Brave, Safari

    Note:
        Window activation may fail if the browser is running with elevated
        privileges or if there are multiple browser instances.
    """
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
    """
    Open browser developer tools for web development and debugging.

    Uses F12 key which is the standard shortcut for developer tools
    in most modern browsers including Chrome, Firefox, and Edge.
    """
    speak("Opening developer tools")
    ui.hotkey("f12")


def toggle_fullscreen():
    """
    Toggle fullscreen mode for the current application.

    Uses F11 key which is the standard shortcut for toggling fullscreen
    mode in most browsers and many other applications.
    """
    speak("Toggling fullscreen")
    ui.hotkey("f11")


def reload_page():
    """
    Reload or refresh the current web page.

    Uses F5 key which is the standard refresh shortcut in web browsers
    and many other applications that display dynamic content.
    """
    speak("Reloading page")
    ui.hotkey("f5")


def go_back():
    """
    Navigate back to the previous page in browser history.

    Uses Alt+Left arrow which is the standard back navigation shortcut
    in most web browsers and file explorers.
    """
    speak("Going back")
    ui.hotkey("alt", "left")


def go_forward():
    """
    Navigate forward to the next page in browser history.

    Uses Alt+Right arrow which is the standard forward navigation shortcut
    in most web browsers and file explorers.
    """
    speak("Going forward")
    ui.hotkey("alt", "right")


def duplicate_tab():
    """
    Duplicate the current browser tab.

    Uses Alt+D to focus the address bar followed by Alt+Enter to open
    the URL in a new tab, effectively duplicating the current tab.

    Process:
        1. Focuses address bar with Alt+D
        2. Opens URL in new tab with Alt+Enter

    Compatibility:
        Works with Chrome, Edge, and other Chromium-based browsers.
        Firefox uses Ctrl+L then Alt+Enter for the same functionality.
    """
    speak("Duplicating tab")
    ui.hotkey("alt", "d")
    time.sleep(0.1)
    ui.hotkey("alt", "enter")
