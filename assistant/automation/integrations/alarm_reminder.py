"""
Alarm and Reminder Management System

This module provides functionality for setting, managing, and triggering alarms and reminders.
"""

import datetime
import threading
import time
import json
import os
import pygame
from assistant.core.speak_selector import speak
from assistant.activities.notification import notification
from assistant.utils.time_parser import parse_relative_time, parse_absolute_time

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


def ensure_data_directory() -> None:
    os.makedirs("data/alarm_data", exist_ok=True)
    os.makedirs("data/reminder_data", exist_ok=True)

def save_alarms() -> None:
    ensure_data_directory()
    try:
        with open(ALARM_FILE, "w") as f:
            json.dump(active_alarms, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving alarms: {e}")

def save_reminders() -> None:
    ensure_data_directory()
    try:
        with open(REMINDER_FILE, "w") as f:
            json.dump(active_reminders, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving reminders: {e}")

def load_alarms() -> None:
    global active_alarms
    try:
        if os.path.exists(ALARM_FILE):
            with open(ALARM_FILE, "r") as f:
                active_alarms = json.load(f)
    except Exception as e:
        print(f"Error loading alarms: {e}")
        active_alarms = {}

def load_reminders() -> None:
    global active_reminders
    try:
        if os.path.exists(REMINDER_FILE):
            with open(REMINDER_FILE, "r") as f:
                active_reminders = json.load(f)
    except Exception as e:
        print(f"Error loading reminders: {e}")
        active_reminders = {}


# Initialize pygame mixer once
pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Warning: mixer init failed: {e}")


def play_audio_file(file_path: str, repeat_times: int = 1) -> None:
    try:
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            os.system("echo -e '\\a'")
            return

        if pygame.mixer.get_init() is None:
            pygame.mixer.init()

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
            os.system("echo -e '\\a'")
        except:
            print("🔔 AUDIO ALERT! 🔔")


def play_alarm_sound() -> None:
    play_audio_file(ALARM_SOUND_FILE, repeat_times=3)

def play_reminder_sound() -> None:
    play_audio_file(REMINDER_SOUND_FILE, repeat_times=3)


def alarm_worker(alarm_id: str, target_time: datetime.datetime, message: str) -> None:
    current_time = datetime.datetime.now()
    wait_time = (target_time - current_time).total_seconds()
    if wait_time > 0:
        time.sleep(wait_time)

    if alarm_id not in active_alarms:
        return

    alarm_message = message if message else "Time's up!"
    notification(title="ALARM!", message=alarm_message)
    play_alarm_sound()

    active_alarms.pop(alarm_id, None)
    save_alarms()
    alarm_threads.pop(alarm_id, None)


def reminder_worker(reminder_id: str, target_time: datetime.datetime, message: str) -> None:
    current_time = datetime.datetime.now()
    wait_time = (target_time - current_time).total_seconds()
    if wait_time > 0:
        time.sleep(wait_time)

    if reminder_id not in active_reminders:
        return

    reminder_message = message if message else "You have a reminder!"
    notification(title="REMINDER!", message=reminder_message)
    play_reminder_sound()

    active_reminders.pop(reminder_id, None)
    save_reminders()
    reminder_threads.pop(reminder_id, None)


def set_alarm(command_text: str) -> None:
    try:
        command_lower = command_text.lower()
        target_time, message = parse_relative_time(command_lower)

        if not target_time:
            target_time, message = parse_absolute_time(command_lower, is_reminder=False)

        if not target_time:
            speak("I couldn't understand the time format. Please try again.")
            return

        alarm_id = f"alarm_{int(time.time())}"
        active_alarms[alarm_id] = {
            "time": target_time.isoformat(),
            "message": message,
            "created": datetime.datetime.now().isoformat(),
        }

        thread = threading.Thread(target=alarm_worker, args=(alarm_id, target_time, message))
        thread.daemon = True
        thread.start()
        alarm_threads[alarm_id] = thread
        save_alarms()

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


def set_reminder(command_text: str) -> None:
    try:
        command_lower = command_text.lower()
        target_time, message = parse_relative_time(command_lower)

        if not target_time:
            target_time, message = parse_absolute_time(command_lower, is_reminder=True)

        if not target_time:
            speak("I couldn't understand the time format. Please try again.")
            return

        reminder_id = f"reminder_{int(time.time())}"
        active_reminders[reminder_id] = {
            "time": target_time.isoformat(),
            "message": message,
            "created": datetime.datetime.now().isoformat(),
        }

        thread = threading.Thread(target=reminder_worker, args=(reminder_id, target_time, message))
        thread.daemon = True
        thread.start()
        reminder_threads[reminder_id] = thread
        save_reminders()

        if target_time.date() == datetime.datetime.now().date():
            time_str = target_time.strftime("%I:%M %p")
            speak(f"Reminder set for {time_str} today: {message}")
        else:
            time_str = target_time.strftime("%I:%M %p on %B %d")
            speak(f"Reminder set for {time_str}: {message}")
    except Exception as e:
        print(f"Error setting reminder: {e}")
        speak("Sorry, I couldn't set the reminder. Please try again.")


def list_alarms() -> None:
    if not active_alarms:
        speak("You have no active alarms.")
        return

    speak(f"You have {len(active_alarms)} active alarm{'s' if len(active_alarms) > 1 else ''}:")
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


def list_reminders() -> None:
    if not active_reminders:
        speak("You have no active reminders.")
        return

    speak(f"You have {len(active_reminders)} active reminder{'s' if len(active_reminders) > 1 else ''}:")
    for reminder_id, reminder_data in active_reminders.items():
        reminder_time = datetime.datetime.fromisoformat(reminder_data["time"])
        time_str = reminder_time.strftime("%I:%M %p")

        if reminder_time.date() == datetime.datetime.now().date():
            time_display = f"today at {time_str}"
        else:
            time_display = f"on {reminder_time.strftime('%B %d')} at {time_str}"

        message = reminder_data.get("message", "")
        speak(f"Reminder {time_display}: {message}")


def cancel_all_alarms() -> None:
    global active_alarms, alarm_threads
    count = len(active_alarms)
    active_alarms.clear()
    alarm_threads.clear()
    save_alarms()
    if count > 0:
        speak(f"Cancelled {count} alarm{'s' if count > 1 else ''}.")
    else:
        speak("No active alarms to cancel.")


def cancel_all_reminders() -> None:
    global active_reminders, reminder_threads
    count = len(active_reminders)
    active_reminders.clear()
    reminder_threads.clear()
    save_reminders()
    if count > 0:
        speak(f"Cancelled {count} reminder{'s' if count > 1 else ''}.")
    else:
        speak("No active reminders to cancel.")


load_alarms()
load_reminders()

# --- Command Handlers ---
from assistant.core.registry import on_regex, on_fuzzy

@on_regex(r"(?:set\s+)?(?:an\s+)?alarm\s+(?:for|at|in|after)?\s*(?P<time_text>.*)$")
@on_fuzzy(["set alarm", "wake me up", "alarm at"], score_cutoff=90)
def handle_set_alarm(text):
    set_alarm(text)

@on_regex(r"\b(?:remind\s+me\s+(?:to|about|that)|remember\s+to)\s+(?P<reminder_text>.*)$")
@on_regex(r"\b(?:set\s+)?(?:a\s+)?reminder\s+(?:for|at|in|after)?\s*(?P<reminder_text>.*)$")
@on_fuzzy(["set reminder", "remind me to", "remember to"], score_cutoff=90)
def handle_set_reminder(text):
    set_reminder(text)

@on_fuzzy(["list alarms", "show alarms", "what alarms", "my alarms", "check alarms"], score_cutoff=90)
def handle_list_alarms():
    list_alarms()

@on_fuzzy(["list reminders", "show reminders", "what reminders", "my reminders", "check reminders"], score_cutoff=90)
def handle_list_reminders():
    list_reminders()

@on_fuzzy(["cancel all alarms", "cancel alarm", "delete alarms", "remove alarms", "clear alarms"], score_cutoff=90)
def handle_cancel_alarms():
    cancel_all_alarms()

@on_fuzzy(["cancel all reminders", "cancel reminder", "delete reminders", "remove reminders", "clear reminders"], score_cutoff=90)
def handle_cancel_reminders():
    cancel_all_reminders()
