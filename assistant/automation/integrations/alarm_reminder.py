"""
Alarm and Reminder Management System

This module provides functionality for setting, managing, and triggering alarms and reminders.
It supports both absolute time (e.g., "3:00 PM tomorrow") and relative time (e.g., "in 2 hours") formats.
Alarms and reminders are persisted to JSON files and can be canceled or listed on demand.

Key Features:
- Natural language time parsing
- Persistent storage of alarms and reminders
- Audio and visual notifications
- Thread-based scheduling without blocking main application
- Support for both absolute and relative time expressions
"""

import datetime
import threading
import time
import json
import os
from typing import Optional, Tuple
import re
import pygame
from assistant.core.speak_selector import speak
from assistant.activities.notification import notification

# Global storage for alarms and reminders
active_alarms = {}  # Stores active alarms with their metadata
active_reminders = {}  # Stores active reminders with their metadata
alarm_threads = {}  # Tracks running alarm threads
reminder_threads = {}  # Tracks running reminder threads

# File paths for persistence
ALARM_FILE = "data/alarm_data/alarms.json"  # Path to alarms storage file
REMINDER_FILE = "data/reminder_data/reminders.json"  # Path to reminders storage file

# Audio file paths
ALARM_SOUND_FILE = "data/alarm_data/alarm.mp3"  # Alarm sound file path
REMINDER_SOUND_FILE = "data/reminder_data/reminder.wav"  # Reminder sound file path


def ensure_data_directory():
    """Ensure data directory exists for storing alarm and reminder files"""
    os.makedirs("data/alarm_data", exist_ok=True)
    os.makedirs("data/reminder_data", exist_ok=True)


def save_alarms():
    """Save alarms to JSON file for persistence

    Converts datetime objects to strings and handles file I/O exceptions
    """
    ensure_data_directory()
    try:
        with open(ALARM_FILE, "w") as f:
            json.dump(active_alarms, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving alarms: {e}")


def save_reminders():
    """Save reminders to JSON file for persistence

    Converts datetime objects to strings and handles file I/O exceptions
    """
    ensure_data_directory()
    try:
        with open(REMINDER_FILE, "w") as f:
            json.dump(active_reminders, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving reminders: {e}")


def load_alarms():
    """Load alarms from JSON file into memory

    Restores previously set alarms from persistent storage
    """
    global active_alarms
    try:
        if os.path.exists(ALARM_FILE):
            with open(ALARM_FILE, "r") as f:
                active_alarms = json.load(f)
    except Exception as e:
        print(f"Error loading alarms: {e}")
        active_alarms = {}


def load_reminders():
    """Load reminders from JSON file into memory

    Restores previously set reminders from persistent storage
    """
    global active_reminders
    try:
        if os.path.exists(REMINDER_FILE):
            with open(REMINDER_FILE, "r") as f:
                active_reminders = json.load(f)
    except Exception as e:
        print(f"Error loading reminders: {e}")
        active_reminders = {}


def parse_time(time_str: str) -> Optional[Tuple[int, int]]:
    """Parse time string into (hour, minute) tuple

    Supports multiple time formats:
    - Special words: "noon", "midnight", "midday"
    - 12-hour format: "3:30 PM", "11am", "12:00 p.m."
    - 24-hour format: "15:30", "23:00"
    - Hour only: "3", "15"

    Args:
        time_str: String containing time information

    Returns:
        Tuple of (hour, minute) in 24-hour format, or None if parsing fails
    """
    time_str = time_str.lower().strip()

    # Handle special time words
    special_times = {"noon": (12, 0), "midnight": (0, 0), "midday": (12, 0)}

    for special, time_val in special_times.items():
        if special in time_str:
            return time_val

    # Format: "HH:MM AM/PM" with various punctuation
    am_pm_pattern = r"(\d{1,2}):?(\d{0,2})\s*(a\.?m\.?|p\.?m\.?)"
    match = re.search(am_pm_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3).lower().replace(".", "")

        # Fix AM/PM conversion
        if "pm" in period and hour != 12:
            hour += 12
        elif "am" in period and hour == 12:
            hour = 0

        return (hour, minute)

    # Format: "HH:MM" (24-hour)
    time_pattern = r"(\d{1,2}):(\d{2})"
    match = re.search(time_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return (hour, minute)

    # Format: "HH" (just hour)
    hour_pattern = r"(\d{1,2})"
    match = re.search(hour_pattern, time_str)
    if match:
        hour = int(match.group(1))
        return (hour, 0)

    return None


def parse_duration(duration_str: str) -> Optional[int]:
    """Parse duration string into total minutes

    Supports various duration formats:
    - Decimal hours: "1.5 hours", "2.25 hours"
    - Common expressions: "half an hour", "quarter hour"
    - Minutes: "30 minutes", "45 mins", "in 15 minutes"
    - Hours: "2 hours", "3 hrs", "in 1 hour"
    - Mixed: "1 hour 30 minutes", "2 hrs 15 mins"

    Args:
        duration_str: String containing duration information

    Returns:
        Total minutes as integer, or None if parsing fails
    """
    duration_str = duration_str.lower()

    # Handle decimal hours and minutes
    decimal_hour_pattern = r"(\d+\.\d+)\s*hours?"
    match = re.search(decimal_hour_pattern, duration_str)
    if match:
        hours = float(match.group(1))
        return int(hours * 60)

    # Handle "half an hour", "quarter hour", etc.
    if "half an hour" in duration_str or "half hour" in duration_str:
        return 30
    if "quarter of an hour" in duration_str or "quarter hour" in duration_str:
        return 15

    # Minutes
    minute_patterns = [
        r"(\d+)\s*minutes?",
        r"(\d+)\s*mins?",
        r"in\s*(\d+)\s*minutes?",
        r"after\s*(\d+)\s*minutes?",
    ]
    for pattern in minute_patterns:
        match = re.search(pattern, duration_str)
        if match:
            return int(match.group(1))

    # Hours
    hour_patterns = [
        r"(\d+)\s*hours?",
        r"(\d+)\s*hrs?",
        r"in\s*(\d+)\s*hours?",
        r"after\s*(\d+)\s*hours?",
    ]
    for pattern in hour_patterns:
        match = re.search(pattern, duration_str)
        if match:
            return int(match.group(1)) * 60

    # Mixed format: "1 hour 30 minutes"
    mixed_patterns = [
        r"(\d+)\s*hours?\s*(\d+)\s*minutes?",
        r"(\d+)\s*hrs?\s*(\d+)\s*mins?",
        r"(\d+)\s*hours?\s*and\s*(\d+)\s*minutes?",
        r"(\d+)hr\s*(\d+)min",
    ]
    for pattern in mixed_patterns:
        match = re.search(pattern, duration_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return hours * 60 + minutes

    return None


def parse_relative_time(command_text: str) -> Optional[Tuple[datetime.datetime, str]]:
    """Parse relative time expressions and extract reminder message

    Supports patterns like:
    - "in 2 hours to take medicine"
    - "after 30 minutes that meeting starts"
    - "in 1 hour 15 minutes call John"

    Args:
        command_text: User command containing relative time and optional message

    Returns:
        Tuple of (target_datetime, message) or (None, "") if parsing fails
    """
    command_lower = command_text.lower()

    # Patterns for relative time with message extraction
    patterns = [
        # Pattern: "in X hours to [message]"
        (r"in\s+(\d+\.?\d*)\s*hours?\s+to\s+(.+)", "hours"),
        (r"in\s+(\d+)\s*minutes?\s+to\s+(.+)", "minutes"),
        (r"after\s+(\d+\.?\d*)\s*hours?\s+to\s+(.+)", "hours"),
        (r"after\s+(\d+)\s*minutes?\s+to\s+(.+)", "minutes"),
        # Pattern: "in X hours [message]" (without "to")
        (r"in\s+(\d+\.?\d*)\s*hours?\s+(.+)", "hours"),
        (r"in\s+(\d+)\s*minutes?\s+(.+)", "minutes"),
        (r"after\s+(\d+\.?\d*)\s*hours?\s+(.+)", "hours"),
        (r"after\s+(\d+)\s*minutes?\s+(.+)", "minutes"),
        # Pattern with "that"
        (r"in\s+(\d+\.?\d*)\s*hours?\s+that\s+(.+)", "hours"),
        (r"in\s+(\d+)\s*minutes?\s+that\s+(.+)", "minutes"),
        # Mixed hours and minutes
        (r"in\s+(\d+)\s*hours?\s*(\d+)\s*minutes?\s+to\s+(.+)", "mixed"),
        (r"in\s+(\d+)\s*hours?\s*(\d+)\s*minutes?\s+(.+)", "mixed"),
    ]

    for pattern, pattern_type in patterns:
        match = re.search(pattern, command_lower)
        if match:
            if pattern_type == "hours":
                hours = float(match.group(1))
                message = match.group(2).strip()
                target_time = datetime.datetime.now() + datetime.timedelta(hours=hours)
                return target_time, message
            elif pattern_type == "minutes":
                minutes = int(match.group(1))
                message = match.group(2).strip()
                target_time = datetime.datetime.now() + datetime.timedelta(
                    minutes=minutes
                )
                return target_time, message
            elif pattern_type == "mixed":
                hours = int(match.group(1))
                minutes = int(match.group(2))
                message = match.group(3).strip()
                target_time = datetime.datetime.now() + datetime.timedelta(
                    hours=hours, minutes=minutes
                )
                return target_time, message

    # Simple duration without message
    duration_minutes = parse_duration(command_lower)
    if duration_minutes:
        target_time = datetime.datetime.now() + datetime.timedelta(
            minutes=duration_minutes
        )

        # Try to extract message for simple duration patterns
        message = extract_reminder_message_simple(command_lower, duration_minutes)
        return target_time, message

    return None, ""


def parse_absolute_time(
    command_text: str, is_reminder: bool = False
) -> Optional[Tuple[datetime.datetime, str]]:
    """Parse absolute time expressions with dates and extract message

    Supports:
    - Specific times: "3:00 PM", "14:30"
    - Dates: "tomorrow", "Monday", "December 25th"
    - Combinations: "3 PM tomorrow", "Monday at 9:00 AM"

    Args:
        command_text: User command containing absolute time and optional message
        is_reminder: Whether this is for a reminder (affects message extraction)

    Returns:
        Tuple of (target_datetime, message) or (None, "") if parsing fails
    """
    command_lower = command_text.lower()
    now = datetime.datetime.now()

    # Extract time part first
    time_match = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)", command_lower
    )
    if not time_match:
        return None, ""

    time_str = time_match.group(1)
    parsed_time = parse_time(time_str)
    if not parsed_time:
        return None, ""

    hour, minute = parsed_time

    # Handle dates
    target_date = now.date()

    # Tomorrow
    if "tomorrow" in command_lower:
        target_date += datetime.timedelta(days=1)

    # Day of week
    days_of_week = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    for i, day in enumerate(days_of_week):
        if day in command_lower:
            current_weekday = now.weekday()
            days_ahead = i - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            target_date += datetime.timedelta(days=days_ahead)
            break

    # Specific dates like "December 25th"
    month_patterns = [
        (r"january\s+(\d+)(?:st|nd|rd|th)?", 1),
        (r"february\s+(\d+)(?:st|nd|rd|th)?", 2),
        (r"march\s+(\d+)(?:st|nd|rd|th)?", 3),
        (r"april\s+(\d+)(?:st|nd|rd|th)?", 4),
        (r"may\s+(\d+)(?:st|nd|rd|th)?", 5),
        (r"june\s+(\d+)(?:st|nd|rd|th)?", 6),
        (r"july\s+(\d+)(?:st|nd|rd|th)?", 7),
        (r"august\s+(\d+)(?:st|nd|rd|th)?", 8),
        (r"september\s+(\d+)(?:st|nd|rd|th)?", 9),
        (r"october\s+(\d+)(?:st|nd|rd|th)?", 10),
        (r"november\s+(\d+)(?:st|nd|rd|th)?", 11),
        (r"december\s+(\d+)(?:st|nd|rd|th)?", 12),
    ]

    for pattern, month in month_patterns:
        match = re.search(pattern, command_lower)
        if match:
            day = int(match.group(1))
            try:
                target_date = datetime.date(now.year, month, day)
                # If date has passed this year, set for next year
                if target_date < now.date():
                    target_date = datetime.date(now.year + 1, month, day)
                break
            except ValueError as e:
                print(f"Error creating date: {e}")
                speak("Sorry, that date doesn't seem valid. Please try again.")
                return None, ""

    # Create target datetime
    try:
        target_datetime = datetime.datetime.combine(
            target_date, datetime.time(hour, minute)
        )
    except ValueError as e:
        print(f"Error creating datetime: {e}")
        speak("Sorry, that time doesn't seem valid. Please try again.")
        return None, ""

    # If time has already passed today and no specific future date mentioned,
    # and it's not explicitly for tomorrow or a future date, set for tomorrow
    if (
        target_datetime <= now
        and "tomorrow" not in command_lower
        and not any(day in command_lower for day in days_of_week)
        and not any(pattern[0] in command_lower for pattern in month_patterns)
    ):
        target_datetime += datetime.timedelta(days=1)

    # Extract message - use different logic for reminders vs alarms
    if is_reminder:
        message = extract_reminder_message_absolute(
            command_lower, time_str, target_datetime
        )
    else:
        message = extract_alarm_message_absolute(
            command_lower, time_str, target_datetime
        )

    return target_datetime, message


def extract_reminder_message_simple(command_text: str, duration: int) -> str:
    """Extract message from simple reminder commands without explicit time patterns

    Args:
        command_text: User command text
        duration: Parsed duration in minutes (unused but kept for interface consistency)

    Returns:
        Extracted message or default reminder message
    """
    command_lower = command_text.lower()

    # Remove duration patterns
    temp_text = command_lower

    # Remove duration expressions
    duration_patterns = [
        r"in\s+\d+\.?\d*\s*hours?",
        r"in\s+\d+\s*minutes?",
        r"after\s+\d+\.?\d*\s*hours?",
        r"after\s+\d+\s*minutes?",
        r"in\s+\d+\s*hours?\s*\d*\s*minutes?",
        r"in\s+half\s+an\s+hour",
        r"in\s+half\s+hour",
    ]

    for pattern in duration_patterns:
        temp_text = re.sub(pattern, "", temp_text)

    # Remove reminder command phrases
    reminder_phrases = [
        "remind me",
        "set reminder",
        "reminder",
        "remember to",
        "don't forget to",
        "don't forget",
    ]

    for phrase in reminder_phrases:
        temp_text = temp_text.replace(phrase, "")

    # Remove connecting words
    connecting_words = ["to", "that", "about"]
    for word in connecting_words:
        temp_text = re.sub(rf"\b{word}\b", "", temp_text)

    # Clean up
    message = re.sub(r"\s+", " ", temp_text).strip()
    message = re.sub(r"^[,\s:-]+|[,\s:-]+$", "", message)

    if message and len(message) > 2:
        return message
    else:
        return "You have a reminder!"


def extract_reminder_message_absolute(
    command_text: str, time_str: str, target_time: datetime.datetime
) -> str:
    """Extract message from absolute time reminder commands

    Args:
        command_text: User command text
        time_str: The parsed time string that was extracted
        target_time: The target datetime for the reminder

    Returns:
        Extracted message or default reminder message
    """
    temp_text = command_text.lower()

    # Remove the time string
    temp_text = temp_text.replace(time_str, "")

    # Remove date references
    date_phrases = [
        "tomorrow",
        "today",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    for phrase in date_phrases:
        temp_text = re.sub(rf"\b{phrase}\b", "", temp_text)

    # Remove reminder command phrases
    reminder_phrases = [
        "remind me",
        "set reminder",
        "reminder for",
        "reminder at",
        "remember to",
        "don't forget to",
        "don't forget",
        "set a reminder to",
    ]

    for phrase in reminder_phrases:
        temp_text = temp_text.replace(phrase, "")

    # Remove connecting words that often come before messages
    connecting_words = ["that", "about", "to", "for", "at", "in", "on"]
    for word in connecting_words:
        temp_text = re.sub(rf"\b{word}\b", "", temp_text)

    # Clean up
    message = re.sub(r"\s+", " ", temp_text).strip()
    message = re.sub(r"^[,\s:-]+|[,\s:-]+$", "", message)

    # If we have a reasonable message, return it
    if message and len(message) > 3 and not message.isdigit():
        return message
    else:
        return "You have a reminder!"


def extract_alarm_message_absolute(
    command_text: str, time_str: str, target_time: datetime.datetime
) -> str:
    """Extract message from absolute time alarm commands

    Args:
        command_text: User command text
        time_str: The parsed time string that was extracted
        target_time: The target datetime for the alarm

    Returns:
        Extracted message or default alarm message
    """
    temp_text = command_text.lower()

    # Remove the time string
    temp_text = temp_text.replace(time_str, "")

    # Remove date references
    date_phrases = [
        "tomorrow",
        "today",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    for phrase in date_phrases:
        temp_text = re.sub(rf"\b{phrase}\b", "", temp_text)

    # Remove alarm command phrases
    alarm_phrases = [
        "set alarm for",
        "set an alarm for",
        "alarm for",
        "alarm at",
        "wake me at",
        "wake me",
        "wake up at",
    ]

    for phrase in alarm_phrases:
        temp_text = temp_text.replace(phrase, "")

    # Remove connecting words that often come before messages
    connecting_words = [
        "because",
        "that",
        "about",
        "to",
        "for",
        "at",
        "in",
        "on",
        "with message",
        "saying",
    ]
    for word in connecting_words:
        temp_text = re.sub(rf"\b{word}\b", "", temp_text)

    # Clean up
    message = re.sub(r"\s+", " ", temp_text).strip()
    message = re.sub(r"^[,\s:-]+|[,\s:-]+$", "", message)

    # If we have a reasonable message, return it
    if message and len(message) > 3 and not message.isdigit():
        return message
    else:
        return "Time's up!"


# Initialize pygame mixer once
pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Warning: mixer init failed: {e}")


def play_audio_file(file_path: str, repeat_times: int = 1):
    """Play an audio file using pygame mixer

    Args:
        file_path: Path to the audio file to play
        repeat_times: Number of times to repeat the sound
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            os.system("echo -e '\\a'")  # System bell fallback
            return

        if pygame.mixer.get_init() is None:
            pygame.mixer.init()

        # Load and play the sound
        sound = pygame.mixer.Sound(file_path)

        for _ in range(repeat_times):
            channel = sound.play()
            while channel.get_busy():
                time.sleep(0.1)
            if repeat_times > 1:
                time.sleep(0.5)

    except Exception as e:
        print(f"Error playing audio file {file_path}: {e}")
        try:
            # Try system bell as fallback
            os.system("echo -e '\\a'")
        except:
            # Final fallback - just print
            print("🔔 AUDIO ALERT! 🔔")


def play_alarm_sound():
    """Play alarm sound from data/alarm.mp3 with repetition"""
    play_audio_file(ALARM_SOUND_FILE, repeat_times=3)


def play_reminder_sound():
    """Play reminder sound from data/reminder.mp3 with repetition"""
    play_audio_file(REMINDER_SOUND_FILE, repeat_times=3)


def alarm_worker(alarm_id: str, target_time: datetime.datetime, message: str):
    """Worker thread function for alarm execution

    Waits until target time, then triggers notification and sound.
    Cleans up alarm data after execution.

    Args:
        alarm_id: Unique identifier for the alarm
        target_time: Datetime when alarm should trigger
        message: Alarm message to display
    """
    current_time = datetime.datetime.now()
    wait_time = (target_time - current_time).total_seconds()

    if wait_time > 0:
        time.sleep(wait_time)

    # Trigger alarm
    alarm_message = message if message else "Time's up!"
    notification(title="ALARM!", message=alarm_message)
    play_alarm_sound()

    # Remove from active alarms
    active_alarms.pop(alarm_id, None)
    save_alarms()
    alarm_threads.pop(alarm_id, None)


def reminder_worker(reminder_id: str, target_time: datetime.datetime, message: str):
    """Worker thread function for reminder execution

    Waits until target time, then triggers notification and sound.
    Cleans up reminder data after execution.

    Args:
        reminder_id: Unique identifier for the reminder
        target_time: Datetime when reminder should trigger
        message: Reminder message to display
    """
    current_time = datetime.datetime.now()
    wait_time = (target_time - current_time).total_seconds()

    if wait_time > 0:
        time.sleep(wait_time)

    # Trigger reminder
    reminder_message = message if message else "You have a reminder!"
    notification(title="REMINDER!", message=reminder_message)
    play_reminder_sound()

    # Remove from active reminders
    active_reminders.pop(reminder_id, None)
    save_reminders()
    reminder_threads.pop(reminder_id, None)


def set_alarm(command_text: str):
    """Set an alarm based on natural language command

    Parses the command text to determine alarm time and optional message,
    then creates a background thread to handle the alarm execution.

    Args:
        command_text: User command containing alarm time and optional message
    """
    try:
        command_lower = command_text.lower()

        # Try to parse as relative time first (e.g., "in 2 hours")
        target_time, message = parse_relative_time(command_lower)

        # If not relative or no message captured, try absolute time
        if not target_time:
            target_time, message = parse_absolute_time(command_lower, is_reminder=False)

        if not target_time:
            speak("I couldn't understand the time format. Please try again.")
            return

        # Create unique alarm ID
        alarm_id = f"alarm_{int(time.time())}"

        # Store alarm
        active_alarms[alarm_id] = {
            "time": target_time.isoformat(),
            "message": message,
            "created": datetime.datetime.now().isoformat(),
        }

        # Start alarm thread
        thread = threading.Thread(
            target=alarm_worker, args=(alarm_id, target_time, message)
        )
        thread.daemon = True
        thread.start()
        alarm_threads[alarm_id] = thread

        # Save to file
        save_alarms()

        # Confirm to user
        if target_time.date() == datetime.datetime.now().date():
            time_str = target_time.strftime("%I:%M %p")
            if message and message != "Time's up!":
                speak(f"Alarm set for {time_str} today with message: {message}")
            else:
                speak(f"Alarm set for {time_str} today")
        else:
            time_str = target_time.strftime("%I:%M %p on %B %d")
            if message and message != "Time's up!":
                speak(f"Alarm set for {time_str} with message: {message}")
            else:
                speak(f"Alarm set for {time_str}")

    except Exception as e:
        print(f"Error setting alarm: {e}")
        speak("Sorry, I couldn't set the alarm. Please try again.")


def set_reminder(command_text: str):
    """Set a reminder based on natural language command

    Parses the command text to determine reminder time and message,
    then creates a background thread to handle the reminder execution.

    Args:
        command_text: User command containing reminder time and message
    """
    try:
        command_lower = command_text.lower()

        # Try to parse as relative time first (e.g., "in 2 hours")
        target_time, message = parse_relative_time(command_lower)

        # If not relative or no message captured, try absolute time
        if not target_time:
            target_time, message = parse_absolute_time(command_lower, is_reminder=True)

        if not target_time:
            speak("I couldn't understand the time format. Please try again.")
            return

        # Create unique reminder ID
        reminder_id = f"reminder_{int(time.time())}"

        # Store reminder
        active_reminders[reminder_id] = {
            "time": target_time.isoformat(),
            "message": message,
            "created": datetime.datetime.now().isoformat(),
        }

        # Start reminder thread
        thread = threading.Thread(
            target=reminder_worker, args=(reminder_id, target_time, message)
        )
        thread.daemon = True
        thread.start()
        reminder_threads[reminder_id] = thread

        # Save to file
        save_reminders()

        # Confirm to user
        if target_time.date() == datetime.datetime.now().date():
            time_str = target_time.strftime("%I:%M %p")
            speak(f"Reminder set for {time_str} today: {message}")
        else:
            time_str = target_time.strftime("%I:%M %p on %B %d")
            speak(f"Reminder set for {time_str}: {message}")

    except Exception as e:
        print(f"Error setting reminder: {e}")
        speak("Sorry, I couldn't set the reminder. Please try again.")


def list_alarms():
    """List all active alarms with their times and messages

    Reads from active_alarms global dictionary and announces
    each alarm using text-to-speech
    """
    if not active_alarms:
        speak("You have no active alarms.")
        return

    speak(
        f"You have {len(active_alarms)} active alarm{'s' if len(active_alarms) > 1 else ''}:"
    )

    for alarm_id, alarm_data in active_alarms.items():
        alarm_time = datetime.datetime.fromisoformat(alarm_data["time"])
        time_str = alarm_time.strftime("%I:%M %p")

        if alarm_time.date() == datetime.datetime.now().date():
            time_display = f"today at {time_str}"
        else:
            time_display = f"on {alarm_time.strftime('%B %d')} at {time_str}"

        message = alarm_data.get("message", "")
        if message:
            speak(f"Alarm {time_display} with message: {message}")
        else:
            speak(f"Alarm {time_display}")


def list_reminders():
    """List all active reminders with their times and messages

    Reads from active_reminders global dictionary and announces
    each reminder using text-to-speech
    """
    if not active_reminders:
        speak("You have no active reminders.")
        return

    speak(
        f"You have {len(active_reminders)} active reminder{'s' if len(active_reminders) > 1 else ''}:"
    )

    for reminder_id, reminder_data in active_reminders.items():
        reminder_time = datetime.datetime.fromisoformat(reminder_data["time"])
        time_str = reminder_time.strftime("%I:%M %p")

        if reminder_time.date() == datetime.datetime.now().date():
            time_display = f"today at {time_str}"
        else:
            time_display = f"on {reminder_time.strftime('%B %d')} at {time_str}"

        message = reminder_data.get("message", "")
        speak(f"Reminder {time_display}: {message}")


def cancel_all_alarms():
    """Cancel all active alarms and stop their threads

    Clears the active_alarms dictionary, stops all alarm threads,
    and updates the persistent storage
    """
    global active_alarms, alarm_threads

    count = len(active_alarms)
    active_alarms.clear()
    alarm_threads.clear()
    save_alarms()

    if count > 0:
        speak(f"Cancelled {count} alarm{'s' if count > 1 else ''}.")
    else:
        speak("No active alarms to cancel.")


def cancel_all_reminders():
    """Cancel all active reminders and stop their threads

    Clears the active_reminders dictionary, stops all reminder threads,
    and updates the persistent storage
    """
    global active_reminders, reminder_threads

    count = len(active_reminders)
    active_reminders.clear()
    reminder_threads.clear()
    save_reminders()

    if count > 0:
        speak(f"Cancelled {count} reminder{'s' if count > 1 else ''}.")
    else:
        speak("No active reminders to cancel.")


# Initialize data on module load
load_alarms()
load_reminders()
