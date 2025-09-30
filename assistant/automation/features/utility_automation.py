import os
import psutil
from assistant.core.speak_selector import speak
import pyautogui as ui
import screen_brightness_control as sbc
import datetime


def handle_write(text):
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
    speak("Writing...")
    write_text = text.replace("write", "").replace("right", "").strip()
    if write_text:
        ui.write(write_text)
    else:
        speak("I didn't hear any text to write")


def handle_volume_change(direction):
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
        speak("Volume increased")
    else:
        for _ in range(3):
            ui.press("volumedown")
        speak("Volume decreased")


def handle_brightness(command_text):
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
        speak(f"Brightness increased to {new_brightness}%")
    elif "decrease" in command_text or "down" in command_text:
        current_brightness = sbc.get_brightness()[0]
        new_brightness = max(0, current_brightness - 20)
        sbc.set_brightness(new_brightness)
        speak(f"Brightness decreased to {new_brightness}%")
    else:
        current_brightness = sbc.get_brightness()[0]
        speak(f"Current brightness is {current_brightness}%")


def take_screenshot():
    """
    Capture a screenshot and save it with timestamp to a dedicated directory.
    
    Takes a full-screen screenshot and saves it as a PNG file in the
    Screenshots folder with a filename containing the date and time.
    
    File Naming:
        Format: screenshot_YYYYMMDD_HHMMSS.png
        Example: screenshot_20231201_143022.png
    
    Save Location:
        C:\\Users\\arnab\\OneDrive\\Pictures\\Screenshots
    
    Process:
        1. Ensures the screenshot directory exists
        2. Generates timestamp-based filename
        3. Captures full screen screenshot
        4. Saves as PNG format
        5. Provides voice confirmation
    
    Example:
        >>> take_screenshot()
        # Saves: C:\\Users\\arnab\\OneDrive\\Pictures\\Screenshots\\screenshot_20231201_143022.png
        # Speaks: "Screenshot taken and saved as screenshot_20231201_143022.png"
    """
    screenshot_dir = r"C:\Users\arnab\OneDrive\Pictures\Screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    full_path = os.path.join(screenshot_dir, filename)

    screenshot = ui.screenshot()
    screenshot.save(full_path)
    speak(f"Screenshot taken and saved as {filename}")


def get_system_info():
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


def get_running_apps_windows():
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


def check_running_app():
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