import random
from data.dlg_data.dlg import welcomedlg
from assistant.core.speak_selector import speak


def welcome():
    welcome_message = random.choice(welcomedlg)
    speak(welcome_message)
