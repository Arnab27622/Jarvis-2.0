"""
Module for handling application closure commands via voice or system shortcuts.
"""
import pyautogui as ui
import random
import psutil
from assistant.core.speak_selector import notify
from data.dlg_data.dlg import closedlg
from typing import Optional
from assistant.core.registry import on_regex, on_fuzzy

def close_command(app_name: Optional[str] = None) -> None:
    """
    Closes an application by name or the currently active window.

    If an app_name is provided, it terminates the process matching that name.
    Otherwise, it triggers the Alt+F4 shortcut to close the active window.
    """
    if app_name:
        notify(f"Closing {app_name}")
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
            notify(f"I couldn't find {app_name} running.")
    else:
        notify(random.choice(closedlg))
        ui.hotkey("alt", "f4")

@on_regex(r"\b(?:close|exit|terminate|kill)\s+(?P<app_name>.+)$")
@on_fuzzy(["close", "exit", "close that", "close app"], score_cutoff=90)
def handle_close(app_name=None):
    """
    Command handler for closing applications via voice input.
    """
    close_command(app_name)
