"""
This module provides functionality to launch local applications and open websites
via voice commands, utilizing system automation and fuzzy matching for user intent.
"""

import os
import pyautogui as ui
import webbrowser
import time
import random
import difflib
from assistant.core.speak_selector import notify
from data.dlg_data.dlg import open_dlg, open_website_maybe, sorry_web, websites

common_apps = {
    "notepad": "notepad",
    "calculator": "calc",
    "command prompt": "cmd",
    "terminal": "wt",
    "paint": "mspaint",
    "explorer": "explorer",
    "file explorer": "explorer",
    "settings": "ms-settings:",
    "task manager": "taskmgr",
    "control panel": "control",
    "wordpad": "write",
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox"
}


def appOpen(text: str) -> bool:
    """
    Launches a local application using system commands or Start menu automation.

    Args:
        text: The name of the application to launch.

    Returns:
        True if the launch sequence was initiated, False otherwise.
    """
    try:
        clean_name = text.lower().strip()
        notify(f"{random.choice(open_dlg)} {text}")
        
        if clean_name in common_apps:
            os.system(f"start {common_apps[clean_name]}")
            return True
            
        ui.press("win")
        time.sleep(0.7)
        ui.write(text, interval=0.05)
        time.sleep(0.5)
        ui.press("enter")
        return True
    except Exception as e:
        notify(f"Failed to open application {text}. Error: {str(e)}")
        return False


def webOpen(text: str) -> bool:
    """
    Opens a website in the default browser using exact or fuzzy matching.

    Args:
        text: The name of the website to open.

    Returns:
        True if a website was successfully opened, False otherwise.
    """
    text = text.lower().strip()

    if text in websites:
        notify(f"{random.choice(open_dlg)} {text}")
        webbrowser.open(websites[text])
        return True

    matches = difflib.get_close_matches(text, websites.keys(), n=1, cutoff=0.6)
    if matches:
        closest_match = matches[0]
        notify(f"{random.choice(open_website_maybe)} {closest_match}")
        webbrowser.open(websites[closest_match])
        return True

    notify(f"{random.choice(sorry_web)} {text}")
    return False


def open_command(text: str) -> None:
    """
    Routes the open request to either an application or a website handler.

    Args:
        text: The target name provided by the user.
    """
    clean_text = text.lower().strip()

    if clean_text == "":
        notify("Please specify what you want to open.")
        return

    is_known_website = clean_text in websites or difflib.get_close_matches(
        clean_text, websites.keys(), n=1, cutoff=0.6
    )

    if is_known_website:
        webOpen(text)
    else:
        app_success = appOpen(clean_text)

        if not app_success:
            web_success = webOpen(text)

            if not web_success:
                notify(f"I couldn't find an application or website named {clean_text}.")


if __name__ == "__main__":
    open_command("open abc")


from assistant.core.registry import on_regex

@on_regex(r"\b(?:open|launch|start)\s+(?P<target>.*)$")
def handle_open(target):
    """
    Regex-based handler for triggering the open command via assistant input.
    """
    open_command(target)
