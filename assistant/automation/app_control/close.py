import pyautogui as ui
import random
from assistant.core.speak_selector import speak
from data.dlg_data.dlg import closedlg


def close_command():
    speak(random.choice(closedlg))
    ui.hotkey("alt", "f4")
