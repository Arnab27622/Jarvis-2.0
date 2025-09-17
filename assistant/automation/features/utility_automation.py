import os
import psutil
from assistant.core.speak_selector import speak
import pyautogui as ui
import screen_brightness_control as sbc
import datetime


def handle_write(text):
    """Handle text writing commands"""
    speak("Writing...")
    write_text = text.replace("write", "").replace("right", "").strip()
    if write_text:
        ui.write(write_text)
    else:
        speak("I didn't hear any text to write")


def handle_volume_change(direction):
    """Handle volume changes with more controlled increments"""
    if direction == "increase":
        for _ in range(3):
            ui.press("volumeup")
        speak("Volume increased")
    else:
        for _ in range(3):
            ui.press("volumedown")
        speak("Volume decreased")


def handle_brightness(command_text):
    """Adjust screen brightness"""
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
    """Take a screenshot and save it with timestamp in the specified directory"""
    screenshot_dir = r"C:\Users\arnab\OneDrive\Pictures\Screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    full_path = os.path.join(screenshot_dir, filename)

    screenshot = ui.screenshot()
    screenshot.save(full_path)
    speak(f"Screenshot taken and saved as {filename}")


def get_system_info():
    """Get basic system information"""
    battery = psutil.sensors_battery()
    percent = battery.percent if battery else "unknown"
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    speak(f"Battery is at {percent} percent. Memory usage is {memory_percent} percent")
