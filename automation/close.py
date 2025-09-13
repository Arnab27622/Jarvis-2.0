import pyautogui as ui
import sys
from pathlib import Path
import random


current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from head.mouth import speak
from data.dlg_data.dlg import closedlg


def close_command():
    speak(random.choice(closedlg))
    ui.hotkey("alt", "f4")
