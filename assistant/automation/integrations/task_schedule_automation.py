import datetime
from assistant.core.speak_selector import speak

# Global dictionary to store remembered information with timestamps
# Structure: {timestamp: information}
remembered_info = {}


def remember_info(command_text):
    """
    Store user-provided information with automatic timestamping for later recall.

    This function extracts information from voice commands and stores it in a
    global dictionary with the current timestamp as the key. Useful for
    remembering notes, reminders, or important information during a session.

    Args:
        command_text (str): The voice command containing information to remember.
                          Expected format: "remember that [information]"

    Process:
        1. Extracts information by removing the "remember that" trigger phrase
        2. Generates a timestamp for when the information was stored
        3. Stores the information in the global remembered_info dictionary
        4. Provides voice confirmation of successful storage

    Example:
        >>> remember_info("remember that my meeting is at 3 PM tomorrow")
        # Stores: {'2024-01-15 14:30:25': 'my meeting is at 3 PM tomorrow'}
        # Speaks: "I've remembered that information"

    Storage:
        Information is stored in memory only and will be lost when the
        application restarts. For persistent storage, consider integrating
        with a database or file system.
    """
    # Extract the actual information by removing the command trigger phrase
    info = command_text.replace("remember that", "").strip()
    if info:
        # Create timestamp in human-readable format for easy recall
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        remembered_info[timestamp] = info
        speak("I've remembered that information")
    else:
        speak("What would you like me to remember?")


def recall_info():
    """
    Recall and announce all previously stored information with timestamps.

    This function retrieves all information stored via the remember_info function
    and presents it in chronological order with timestamps. Each piece of
    information is announced separately for clarity.

    Process:
        1. Checks if any information has been stored
        2. If information exists, announces each item with its timestamp
        3. If no information exists, informs the user nothing is stored
        4. Presents information in the order it was stored (by timestamp)

    Example Output:
        "You asked me to remember the following:"
        "On 2024-01-15 14:30:25, you said: my meeting is at 3 PM tomorrow"
        "On 2024-01-15 15:45:10, you said: buy milk on the way home"

    Note:
        This function only recalls information stored during the current
        application session. Information is not persisted across restarts.
    """
    if remembered_info:
        speak("You asked me to remember the following:")
        # Iterate through all stored information with timestamps
        for timestamp, info in remembered_info.items():
            speak(f"On {timestamp}, you said: {info}")
    else:
        speak("I don't have any information stored to recall")
