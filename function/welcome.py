import sys
from pathlib import Path
import random

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from data.dlg_data.dlg import welcomedlg
from head.mouth import speak


def welcome():
    welcome_message = random.choice(welcomedlg)
    speak(welcome_message)
