import datetime
import threading
import time
import json
import os
from typing import Optional, Tuple
import re
import pygame
from assistant.core.speak_selector import speak

# Global storage for alarms and reminders
active_alarms = {}
active_reminders = {}
alarm_threads = {}
reminder_threads = {}

# File paths for persistence
ALARM_FILE = "data/alarm_data/alarms.json"
REMINDER_FILE = "data/reminder_data/reminders.json"

# Audio file paths
ALARM_SOUND_FILE = "data/alarm_data/alarm.mp3"
REMINDER_SOUND_FILE = "data/reminder_data/reminder.wav"


def ensure_data_directory():
    """Ensure data directory exists"""
    os.makedirs("data/alarm_data", exist_ok=True)
    os.makedirs("data/reminder_data", exist_ok=True)


def save_alarms():
    """Save alarms to file"""
    ensure_data_directory()
    try:
        with open(ALARM_FILE, "w") as f:
            json.dump(active_alarms, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving alarms: {e}")


def save_reminders():
    """Save reminders to file"""
    ensure_data_directory()
    try:
        with open(REMINDER_FILE, "w") as f:
            json.dump(active_reminders, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving reminders: {e}")


def load_alarms():
    """Load alarms from file"""
    global active_alarms
    try:
        if os.path.exists(ALARM_FILE):
            with open(ALARM_FILE, "r") as f:
                active_alarms = json.load(f)
    except Exception as e:
        print(f"Error loading alarms: {e}")
        active_alarms = {}


def load_reminders():
    """Load reminders from file"""
    global active_reminders
    try:
        if os.path.exists(REMINDER_FILE):
            with open(REMINDER_FILE, "r") as f:
                active_reminders = json.load(f)
    except Exception as e:
        print(f"Error loading reminders: {e}")
        active_reminders = {}


def parse_time(time_str: str) -> Optional[Tuple[int, int]]:
    """Parse time from various formats"""
    time_str = time_str.lower().strip()

    # Format: "HH:MM AM/PM"
    am_pm_pattern = r"(\d{1,2}):?(\d{0,2})\s*(am|pm)"
    match = re.search(am_pm_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
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
    """Parse duration in minutes from text"""
    duration_str = duration_str.lower()

    # Minutes
    minute_patterns = [r"(\d+)\s*minute", r"(\d+)\s*min"]
    for pattern in minute_patterns:
        match = re.search(pattern, duration_str)
        if match:
            return int(match.group(1))

    # Hours
    hour_patterns = [r"(\d+)\s*hour", r"(\d+)\s*hr"]
    for pattern in hour_patterns:
        match = re.search(pattern, duration_str)
        if match:
            return int(match.group(1)) * 60

    # Mixed format: "1 hour 30 minutes"
    hour_match = re.search(r"(\d+)\s*hour", duration_str)
    minute_match = re.search(r"(\d+)\s*minute", duration_str)
    if hour_match or minute_match:
        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(minute_match.group(1)) if minute_match else 0
        return hours * 60 + minutes

    return None


# Initialize pygame mixer once
pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Warning: mixer init failed: {e}")


def play_audio_file(file_path: str, repeat_times: int = 1):
    """Play an audio file using pygame"""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            os.system("echo -e '\\a'")
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
    """Play alarm sound from data/alarm.mp3"""
    play_audio_file(ALARM_SOUND_FILE, repeat_times=3)


def play_reminder_sound():
    """Play reminder sound from data/reminder.mp3"""
    play_audio_file(REMINDER_SOUND_FILE, repeat_times=1)


def alarm_worker(alarm_id: str, target_time: datetime.datetime, message: str):
    """Worker thread for alarm"""
    current_time = datetime.datetime.now()
    wait_time = (target_time - current_time).total_seconds()

    if wait_time > 0:
        time.sleep(wait_time)

    # Trigger alarm
    alarm_message = f"ALARM! {message}" if message else "ALARM! Time's up!"
    speak(alarm_message)
    play_alarm_sound()

    # Remove from active alarms
    active_alarms.pop(alarm_id, None)
    save_alarms()
    alarm_threads.pop(alarm_id, None)


def reminder_worker(reminder_id: str, target_time: datetime.datetime, message: str):
    """Worker thread for reminder"""
    current_time = datetime.datetime.now()
    wait_time = (target_time - current_time).total_seconds()

    if wait_time > 0:
        time.sleep(wait_time)

    # Trigger reminder
    reminder_message = (
        f"REMINDER: {message}" if message else "REMINDER: You have a reminder!"
    )
    speak(reminder_message)
    play_reminder_sound()

    # Remove from active reminders
    active_reminders.pop(reminder_id, None)
    save_reminders()
    reminder_threads.pop(reminder_id, None)


def set_alarm(command_text: str):
    """Set an alarm based on command text"""
    try:
        # Extract time and message
        command_lower = command_text.lower()

        # Remove "set alarm" part
        for phrase in [
            "set alarm for",
            "set alarm at",
            "set an alarm for",
            "set an alarm at",
            "alarm for",
            "alarm at",
        ]:
            if phrase in command_lower:
                time_part = command_lower.split(phrase, 1)[1].strip()
                break
        else:
            speak("I couldn't understand the time format. Please try again.")
            return

        # Split by common separators to get time and message
        message = ""
        time_str = time_part
        for separator in [" with message ", " to ", " for ", " saying ", " reminder "]:
            if separator in time_part:
                parts = time_part.split(separator, 1)
                time_str = parts[0].strip()
                message = parts[1].strip()
                break

        # Parse the time
        parsed_time = parse_time(time_str)
        if not parsed_time:
            speak(
                "I couldn't understand the time format. Please use formats like '3:30 PM' or '15:30'."
            )
            return

        hour, minute = parsed_time

        # Create target datetime
        now = datetime.datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time has already passed today, set for tomorrow
        if target_time <= now:
            target_time += datetime.timedelta(days=1)

        # Create unique alarm ID
        alarm_id = f"alarm_{int(time.time())}"

        # Store alarm
        active_alarms[alarm_id] = {
            "time": target_time.isoformat(),
            "message": message,
            "created": now.isoformat(),
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
        time_str = target_time.strftime("%I:%M %p")
        if message:
            speak(f"Alarm set for {time_str} with message: {message}")
        else:
            speak(f"Alarm set for {time_str}")

    except Exception as e:
        print(f"Error setting alarm: {e}")
        speak("Sorry, I couldn't set the alarm. Please try again.")


def set_reminder(command_text: str):
    """Set a reminder based on command text"""
    try:
        command_lower = command_text.lower()

        # Extract reminder details
        message = ""
        target_time = None

        # Check if it's a time-based reminder
        for phrase in [
            "remind me at",
            "reminder at",
            "remind me to",
            "set reminder for",
            "reminder for",
        ]:
            if phrase in command_lower:
                rest = command_lower.split(phrase, 1)[1].strip()

                if phrase in ["remind me at", "reminder at"]:
                    # Time-based reminder
                    parts = rest.split(" to ", 1)
                    if len(parts) == 2:
                        time_str = parts[0].strip()
                        message = parts[1].strip()
                    else:
                        time_str = rest
                        message = "You have a reminder!"

                    parsed_time = parse_time(time_str)
                    if parsed_time:
                        hour, minute = parsed_time
                        now = datetime.datetime.now()
                        target_time = now.replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                        if target_time <= now:
                            target_time += datetime.timedelta(days=1)

                else:
                    # Duration-based reminder
                    duration = parse_duration(rest)
                    if duration:
                        target_time = datetime.datetime.now() + datetime.timedelta(
                            minutes=duration
                        )
                        message = f"Reminder after {duration} minutes"
                    else:
                        # Try to extract both duration and message
                        for word in rest.split():
                            if any(
                                time_word in word
                                for time_word in ["minute", "min", "hour", "hr"]
                            ):
                                duration_part = " ".join(
                                    rest.split()[: rest.split().index(word) + 1]
                                )
                                message_part = " ".join(
                                    rest.split()[rest.split().index(word) + 1 :]
                                )
                                duration = parse_duration(duration_part)
                                if duration:
                                    target_time = (
                                        datetime.datetime.now()
                                        + datetime.timedelta(minutes=duration)
                                    )
                                    message = (
                                        message_part.strip()
                                        or f"Reminder after {duration} minutes"
                                    )
                                break
                break

        if not target_time:
            speak(
                "I couldn't understand when to set the reminder. Please specify a time or duration."
            )
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
            speak(f"Reminder set for {time_str}: {message}")
        else:
            time_str = target_time.strftime("%I:%M %p on %B %d")
            speak(f"Reminder set for {time_str}: {message}")

    except Exception as e:
        print(f"Error setting reminder: {e}")
        speak("Sorry, I couldn't set the reminder. Please try again.")


def list_alarms():
    """List all active alarms"""
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
    """List all active reminders"""
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
    """Cancel all active alarms"""
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
    """Cancel all active reminders"""
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
