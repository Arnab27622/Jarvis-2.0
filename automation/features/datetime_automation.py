from head.speak_selector import speak
import datetime


def tell_time():
    """Tell the current time"""
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The current time is {current_time}")


def tell_date():
    """Tell the current date"""
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today is {current_date}")
