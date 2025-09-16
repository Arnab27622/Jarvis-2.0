import pyautogui as ui
import webbrowser
from pathlib import Path
import sys
import time
import random
import difflib

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from assistant.core.speak_selector import speak
from data.dlg_data.dlg import open_dlg, open_website_maybe, sorry_web, websites


def appOpen(text: str) -> bool:
    try:
        speak(f"{random.choice(open_dlg)} {text}")
        ui.press("win")
        time.sleep(0.7)
        ui.write(text)
        time.sleep(0.5)
        ui.press("enter")
        return True
    except Exception as e:
        speak(f"Failed to open application {text}. Error: {str(e)}")
        return False


def webOpen(text: str) -> bool:
    text = text.lower().strip()
    if text in websites:
        speak(f"{random.choice(open_dlg)} {text}")
        webbrowser.open(websites[text])
        return True

    # Fuzzy match
    matches = difflib.get_close_matches(text, websites.keys(), n=1, cutoff=0.6)
    if matches:
        closest_match = matches[0]
        speak(f"{random.choice(open_website_maybe)} {closest_match}")
        webbrowser.open(websites[closest_match])
        return True

    # No match found
    speak(f"{random.choice(sorry_web)} {text}")
    return False


def open_command(text: str) -> None:
    clean_text = text.lower().strip()

    if clean_text == "":
        speak("Please specify what you want to open.")
        return

    # First check if it's a known website
    is_known_website = clean_text in websites or difflib.get_close_matches(
        clean_text, websites.keys(), n=1, cutoff=0.6
    )

    if is_known_website:
        webOpen(text)
    else:
        # Try to open as application first
        app_success = appOpen(clean_text)

        # If app opening fails, try as a website (might be an unknown website)
        if not app_success:
            web_success = webOpen(text)

            # If both fail, provide a final error message
            if not web_success:
                speak(f"I couldn't find an application or website named {clean_text}.")


if __name__ == "__main__":
    open_command("open abc")
