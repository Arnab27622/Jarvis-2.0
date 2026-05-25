import os
import psutil
from assistant.core.speak_selector import speak, notify
import pyautogui as ui
import screen_brightness_control as sbc
import datetime
from assistant.automation.features.window_automation import (
    open_incognito_tab, bookmark_page, open_dev_tools, reload_page,
    go_back, go_forward, duplicate_tab, handle_scroll_to_top,
    handle_scroll_to_bottom, handle_scroll
)
from assistant.activities.check_speaker_health import speaker_health_test
from assistant.activities.check_mic_health import mic_health
from assistant.activities.battery_features import battery_monitor

def handle_write(text: str) -> None:
    """
    Handle text writing commands by typing the specified text.
    
    This function extracts text from voice commands and types it using
    keyboard automation. Useful for hands-free text entry in any application.
    
    Args:
        text (str): The voice command containing text to write.
                   Expected format: "write [text]" or "right [text]"
    
    Process:
        1. Removes command keywords ("write", "right") from the input
        2. Strips whitespace from the remaining text
        3. Uses pyautogui to type the extracted text
        4. Provides voice feedback on success or failure
    
    Example:
        >>> handle_write("write hello world")
        # Types: "hello world"
        # Speaks: "Writing..."
    
    Note:
        The function will type text in whatever application currently has focus.
        Ensure the correct text field is active before using this command.
    """
    notify("Writing...")
    write_text = text.replace("write", "").replace("right", "").strip()
    if write_text:
        ui.write(write_text, interval=0.05)
    else:
        notify("I didn't hear any text to write")


def handle_volume_change(direction: str) -> None:
    """
    Adjust system volume with controlled increments.
    
    Changes the system volume by sending multiple volume key presses
    for more noticeable changes than single key presses.
    
    Args:
        direction (str): Either "increase" to raise volume or "decrease" to lower volume
    
    Behavior:
        - Increase: Sends 3 volume up key presses
        - Decrease: Sends 3 volume down key presses
        - Provides voice confirmation of the action
    
    Example:
        >>> handle_volume_change("increase")
        # Presses volume up 3 times
        # Speaks: "Volume increased"
    
    Note:
        The actual volume change depends on system volume step settings.
        This uses the default system volume controls.
    """
    if direction == "increase":
        for _ in range(3):
            ui.press("volumeup")
        notify("Volume increased")
    else:
        for _ in range(3):
            ui.press("volumedown")
        notify("Volume decreased")


def handle_brightness(command_text: str) -> None:
    """
    Adjust or query screen brightness levels.
    
    Controls screen brightness with 20% increments/decrements or reports
    the current brightness level when no change is specified.
    
    Args:
        command_text (str): Voice command containing brightness instructions.
                          Supported commands:
                          - "increase brightness" or "brightness up"
                          - "decrease brightness" or "brightness down"
                          - Any other text: reports current brightness
    
    Behavior:
        - Increase: Raises brightness by 20% (capped at 100%)
        - Decrease: Lowers brightness by 20% (capped at 0%)
        - Query: Reports current brightness percentage
    
    Example:
        >>> handle_brightness("increase brightness")
        # If current is 50%, sets to 70%
        # Speaks: "Brightness increased to 70%"
    
    Dependencies:
        Requires screen_brightness_control package for brightness manipulation.
    """
    if "increase" in command_text or "up" in command_text:
        current_brightness = sbc.get_brightness()[0]
        new_brightness = min(100, current_brightness + 20)
        sbc.set_brightness(new_brightness)
        notify(f"Brightness increased to {new_brightness}%")
    elif "decrease" in command_text or "down" in command_text:
        current_brightness = sbc.get_brightness()[0]
        new_brightness = max(0, current_brightness - 20)
        sbc.set_brightness(new_brightness)
        notify(f"Brightness decreased to {new_brightness}%")
    else:
        current_brightness = sbc.get_brightness()[0]
        notify(f"Current brightness is {current_brightness}%")


def take_screenshot() -> None:
    """
    Capture a screenshot and save it with timestamp to a dedicated directory.
    
    Takes a full-screen screenshot and saves it as a PNG file in the
    Screenshots folder with a filename containing the date and time.
    
    File Naming:
        Format: screenshot_YYYYMMDD_HHMMSS.png
        Example: screenshot_20231201_143022.png
    
    Save Location:
        "C:\\Users\\ARNAB DEY\\Pictures\\Screenshots"
    
    Process:
        1. Ensures the screenshot directory exists
        2. Generates timestamp-based filename
        3. Captures full screen screenshot
        4. Saves as PNG format
        5. Provides voice confirmation
    
    Example:
        >>> take_screenshot()
        # Saves: C:\\Users\\ARNAB DEY\\Pictures\\Screenshots\\screenshot_20231201_143022.png
        # Speaks: "Screenshot taken and saved as screenshot_20231201_143022.png"
    """
    # Calculate project root (4 levels up from this file)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    screenshot_dir = os.path.join(project_root, "data", "screenshots")

    os.makedirs(screenshot_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    full_path = os.path.join(screenshot_dir, filename)

    screenshot = ui.screenshot()
    screenshot.save(full_path)
    notify(f"Screenshot taken and saved as {filename}")


def get_system_info() -> None:
    """
    Provide voice report of key system information.
    
    Reports current battery percentage and memory usage to give the user
    a quick overview of system status without visual interface.
    
    Information Provided:
        - Battery charge percentage (if available)
        - System memory (RAM) usage percentage
    
    Example Output:
        "Battery is at 85 percent. Memory usage is 45 percent"
    
    Note:
        Battery information may not be available on desktop computers
        without battery hardware. In such cases, reports "unknown" for battery.
    """
    battery = psutil.sensors_battery()
    percent = battery.percent if battery else "unknown"
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    speak(f"Battery is at {percent} percent. Memory usage is {memory_percent} percent")


from typing import List, Union

def get_running_apps_windows() -> Union[List[str], str]:
    """
    Retrieve a list of currently running applications on Windows.
    
    Uses psutil to iterate through all running processes and collect
    their executable names. This provides a snapshot of active applications.
    
    Returns:
        list or str: List of application names if successful, 
                    error message string if an exception occurs
    
    Error Handling:
        - Skips processes that terminate during enumeration
        - Skips processes with restricted access permissions
        - Returns error message as string for other exceptions
    
    Example:
        >>> get_running_apps_windows()
        ['chrome.exe', 'notepad.exe', 'python.exe', ...]
    """
    try:
        processes = set()  # Use set to avoid duplicate process names
        for proc in psutil.process_iter(["name"]):
            try:
                processes.add(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Skip processes that terminate or can't be accessed
                continue
        return list(processes)
    except Exception as e:
        return f"Error: {e}"


def check_running_app() -> None:
    """
    Display currently running applications in the console.
    
    This is primarily a debugging and development function that:
    1. Gets the list of running applications
    2. Prints them to the console for inspection
    3. Handles both successful results and error cases
    
    Usage:
        Useful for verifying the system monitoring capabilities
        or debugging process-related issues.
    
    Output:
        - Success: Prints each application name on a new line
        - Error: Prints the error message
    """
    running_apps = get_running_apps_windows()
    if isinstance(running_apps, str):
        print(running_apps)  # Print error message
    else:
        print("Running Applications:")
        for app in running_apps:
            print(app)


if __name__ == "__main__":
    """
    Test entry point for the utility automation module.
    
    When run as a standalone script, this demonstrates the running
    applications checking functionality. Useful for testing the
    process monitoring capabilities during development.
    """
    check_running_app()

# --- Command Handlers ---
from assistant.core.registry import on_regex, on_fuzzy

@on_fuzzy(["new tab", "open new tab", "open a new tab"], score_cutoff=90)
def handle_new_tab():
    ui.hotkey("ctrl", "t")
    notify("New tab opened")

@on_fuzzy(["incognito", "private tab", "secret mode", "incognito mode"], score_cutoff=90)
def handle_incognito():
    open_incognito_tab()

@on_fuzzy(["bookmark", "bookmark this", "bookmark this page", "save this page"], score_cutoff=90)
def handle_bookmark():
    bookmark_page()

@on_fuzzy(["developer tools", "dev tools", "open dev tools"], score_cutoff=90)
def handle_dev_tools():
    open_dev_tools()

@on_fuzzy(["reload", "refresh", "reload page", "refresh page"], score_cutoff=90)
def handle_reload():
    reload_page()

@on_fuzzy(["go back", "back page", "previous page"], score_cutoff=90)
def handle_back_page():
    go_back()

@on_fuzzy(["go forward", "forward page", "next page"], score_cutoff=90)
def handle_forward_page():
    go_forward()

@on_fuzzy(["duplicate tab", "duplicate the tab", "duplicate this tab"], score_cutoff=90)
def handle_duplicate():
    duplicate_tab()

@on_regex(r"(?P<text>.*brightness.*)$")
def handle_brightness_cmd(text):
    handle_brightness(text)

@on_regex(r"\b(?:please\s+)?\b(?:write|right|type)\s+(?P<content>.*)$")
def handle_writing(content):
    handle_write(content)

@on_fuzzy(["enter", "press enter", "hit enter"], score_cutoff=90)
def handle_enter_key():
    ui.press("enter")

@on_fuzzy(["select all", "select all paragraph", "select everything"], score_cutoff=90)
def handle_select_all():
    ui.hotkey("ctrl", "a")

@on_fuzzy(["cut", "cut this", "cut text"], score_cutoff=90)
def handle_cut():
    ui.hotkey("ctrl", "x")

@on_fuzzy(["copy", "copy this", "copy text"], score_cutoff=90)
def handle_copy_cmd():
    ui.hotkey("ctrl", "c")

@on_fuzzy(["paste", "paste here", "paste this"], score_cutoff=90)
def handle_paste_cmd():
    ui.hotkey("ctrl", "v")

@on_fuzzy(["undo", "undo it", "undo that"], score_cutoff=90)
def handle_undo_cmd():
    ui.hotkey("ctrl", "z")

@on_fuzzy(["redo", "redo it", "redo that"], score_cutoff=90)
def handle_redo_cmd():
    ui.hotkey("ctrl", "y")

@on_fuzzy(["copy last paragraph", "copy the last paragraph"], score_cutoff=90)
def handle_copy_last():
    ui.hotkey("ctrl", "shift", "c")

@on_fuzzy(["screenshot", "take screenshot", "take a screenshot"], score_cutoff=90)
def handle_screenshot_cmd():
    take_screenshot()

@on_fuzzy(["run speaker health test", "check the speaker health", "check speaker health", "check the speaker", "speaker health"], score_cutoff=90)
def handle_speaker_health():
    speaker_health_test()

@on_fuzzy(["run mic health test", "check the mic health", "check mic health", "check the mic", "mic health", "mike health"], score_cutoff=90)
def handle_mic_health_cmd():
    mic_health()

@on_regex(r"(?:scroll|page)\s*(?:to\s+(?:the\s+)?)?\s*(?P<direction>up|down|top|bottom)")
@on_fuzzy(["scroll up", "scroll down", "scroll to top", "scroll to bottom",
           "page up", "page down"], score_cutoff=90)
def handle_scroll_cmd(text=None, direction=None):
    d = (direction or text or "").lower()
    if "top" in d:
        handle_scroll_to_top()
    elif "bottom" in d:
        handle_scroll_to_bottom()
    elif "page" in d and "up" in d:
        notify("Scrolling page up")
        ui.press("pageup")
    elif "page" in d and "down" in d:
        notify("Scrolling page down")
        ui.press("pagedown")
    else:
        handle_scroll(text or d)

@on_regex(r"\b(?P<action>increase|decrease|raise|lower|turn up|turn down|up|down)\b\s*(?:the\s+)?volume")
@on_fuzzy(["increase volume", "volume up", "make it louder", "louder", "up the volume",
           "decrease volume", "volume down", "make it softer", "softer", "lower volume",
           "down the volume", "mute", "mute volume", "turn sound off",
           "unmute", "unmute volume", "turn sound on"], score_cutoff=90)
def handle_system_volume(text=None, action=None):
    cmd = (action or text or "").lower()
    if any(w in cmd for w in ["unmute", "sound on"]):
        ui.hotkey("volumemute")
        notify("Volume unmuted")
    elif any(w in cmd for w in ["mute", "sound off"]):
        notify("Muting volume")
        ui.press("volumemute")
    elif any(w in cmd for w in ["increase", "raise", "turn up", "up", "louder"]):
        handle_volume_change("increase")
    else:
        handle_volume_change("decrease")

@on_fuzzy(["system info", "system status", "computer info"], score_cutoff=90)
def handle_sys_info():
    get_system_info()

@on_fuzzy(["battery percentage", "battery status", "check battery"], score_cutoff=90)
def handle_battery_stat():
    battery_monitor.battery_percentage()

@on_fuzzy(["check running apps", "check the running apps", "what is running"], score_cutoff=90)
def handle_running_apps():
    check_running_app()

@on_fuzzy(["shutdown", "shut down", "turn off computer"], score_cutoff=90)
def handle_shutdown_cmd():
    speak("Shutting down the system in 10 seconds")
    os.system("shutdown /s /t 10")

@on_fuzzy(["restart", "restart computer", "reboot"], score_cutoff=90)
def handle_restart_cmd():
    speak("Restarting the system in 10 seconds")
    os.system("shutdown /r /t 10")

