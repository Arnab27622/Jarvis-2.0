"""
Wish Module - Time-based Greeting System

This module provides context-aware greetings based on the time of day. It automatically
determines the appropriate greeting (good morning, afternoon, evening, or night)
and speaks a randomly selected message from the corresponding dialogue category.

Key Features:
- Time-aware greeting selection
- Four time period categories with customizable messages
- Random variation within each time category
- Integration with system TTS
- Real-time datetime processing

Time Periods:
    05:00 - 11:59: Good Morning
    12:00 - 16:59: Good Afternoon
    17:00 - 20:59: Good Evening
    21:00 - 04:59: Good Night

Usage:
    from assistant.core.wish import wish
    wish()  # Speaks appropriate time-based greeting

Dependencies:
- datetime: For current time determination
- random: For message selection variety
- dlg: Dialogue datasets for different time periods
- speak_selector: For TTS functionality
"""

import datetime
import random
from data.dlg_data.dlg import *
from assistant.core.speak_selector import speak

# Get current date and time for greeting determination
today = datetime.date.today()
formatted_date = today.strftime("%d %b %y")  # Format: 01 Jan 24
nowx = datetime.datetime.now()


def wish():
    """
    Speak an appropriate time-based greeting to the user.

    Analyzes the current hour and selects a random greeting message
    from the corresponding time period category (morning, afternoon,
    evening, or night). Uses TTS to speak the selected greeting.

    Time Logic:
        - Morning: 5:00 AM to 11:59 AM
        - Afternoon: 12:00 PM to 4:59 PM
        - Evening: 5:00 PM to 8:59 PM
        - Night: 9:00 PM to 4:59 AM

    Returns:
        None

    Example:
        >>> wish()  # If called at 10:30 AM
        # Randomly selects and speaks: "Good morning! Ready for the day?"
        # or "Morning! How are you feeling today?" etc.
    """
    current_hour = nowx.hour

    # Determine time period and select appropriate greeting
    if 5 <= current_hour < 12:
        # Morning period (5 AM to 11:59 AM)
        gm_dlg = random.choice(good_morningdlg)
        speak(gm_dlg)
    elif 12 <= current_hour < 17:
        # Afternoon period (12 PM to 4:59 PM)
        ga_dlg = random.choice(good_afternoondlg)
        speak(ga_dlg)
    elif 17 <= current_hour < 21:
        # Evening period (5 PM to 8:59 PM)
        ge_dlg = random.choice(good_eveningdlg)
        speak(ge_dlg)
    else:
        # Night period (9 PM to 4:59 AM)
        gn_dlg = random.choice(good_nightdlg)
        speak(gn_dlg)


if __name__ == "__main__":
    """
    Main execution block for testing the wish functionality.

    When run directly, this module will speak the appropriate
    time-based greeting for testing purposes.

    Usage:
        python wish.py
    """
    wish()
