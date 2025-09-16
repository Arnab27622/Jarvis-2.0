import datetime
from assistant.core.speak_selector import speak

remembered_info = {}


def remember_info(command_text):
    """Remember information provided by the user"""
    info = command_text.replace("remember that", "").strip()
    if info:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        remembered_info[timestamp] = info
        speak("I've remembered that information")
    else:
        speak("What would you like me to remember?")


def recall_info():
    """Recall information that was remembered"""
    if remembered_info:
        speak("You asked me to remember the following:")
        for timestamp, info in remembered_info.items():
            speak(f"On {timestamp}, you said: {info}")
    else:
        speak("I don't have any information stored to recall")
