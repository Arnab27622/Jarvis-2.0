"""
Welcome Module - Random Welcome Message Generator

This module provides personalized welcome functionality by selecting and speaking
random welcome messages from a predefined dialogue dataset. Enhances user experience
with varied greetings to prevent monotony.

Key Features:
- Random selection from multiple welcome messages
- Integration with TTS system via speak_selector
- Simple, single-function interface
- Easy customization through external dialogue data

Usage:
    from assistant.core.welcome import welcome
    welcome()  # Speaks a random welcome message

Dependencies:
- random: For message selection variety
- dlg: Dialogue dataset containing welcome messages
- speak_selector: For TTS functionality
"""

import random
from data.dlg_data.dlg import welcomedlg
from assistant.core.speak_selector import speak


def welcome():
    """
    Speak a randomly selected welcome message to the user.

    Selects a welcome message from the predefined dialogue dataset
    and uses the appropriate TTS engine (online/offline) to speak it.

    Returns:
        None

    Example:
        >>> welcome()
        # Randomly selects and speaks: "Hello! Welcome back!"
        # or "Hi there! Good to see you!" etc.
    """
    welcome_message = random.choice(welcomedlg)
    speak(welcome_message)
