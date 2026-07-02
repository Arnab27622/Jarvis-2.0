"""
Module for parsing natural language time, duration, and reminder messages.
"""

import datetime
import re
from typing import Optional, Tuple

def parse_time(time_str: str) -> Optional[Tuple[int, int]]:
    """Converts a time string into an (hour, minute) tuple."""
    time_str = time_str.lower().strip()

    # Handle special time words
    special_times = {"noon": (12, 0), "midnight": (0, 0), "midday": (12, 0)}

    for special, time_val in special_times.items():
        if special in time_str:
            return time_val

    # Format: "HH:MM AM/PM" or "HHMM AM/PM" or "HH AM/PM"
    am_pm_pattern = r"(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)"
    match = re.search(am_pm_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3).lower().replace(".", "")

        if "pm" in period and hour != 12:
            hour += 12
        elif "am" in period and hour == 12:
            hour = 0

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)
        return None

    # Format: "HHMM" or "HMM" (Military time - 3 or 4 digits)
    if time_str.isdigit():
        if len(time_str) == 4:
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)
        elif len(time_str) == 3:
            hour = int(time_str[0])
            minute = int(time_str[1:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)

    # Format: "HH:MM" (24-hour)
    time_pattern = r"(\d{1,2}):(\d{2})"
    match = re.search(time_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)

    # Format: "HH" (just hour)
    hour_pattern = r"^(\d{1,2})$"
    match = re.search(hour_pattern, time_str)
    if match:
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return (hour, 0)

    return None

def parse_duration(duration_str: str) -> Optional[int]:
    """Converts a duration string into total minutes."""
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

    return None

def extract_reminder_message_simple(command_text: str, duration: int) -> str:
    """Extracts the reminder content from a relative time command."""
    temp_text = command_text.lower()

    duration_patterns = [
        r"in\s+\d+\.?\d*\s*hours?(?:\s*\d+\s*minutes?)?",
        r"after\s+\d+\.?\d*\s*hours?(?:\s*\d+\s*minutes?)?",
        r"in\s+\d+\s*minutes?",
        r"after\s+\d+\s*minutes?",
        r"in\s+half\s+an\s+hour",
        r"in\s+half\s+hour",
    ]
    for pattern in duration_patterns:
        temp_text = re.sub(pattern, "", temp_text)

    action_phrases = [
        "set a reminder", "set reminder", "reminder", "remind me", 
        "remember", "don't forget", "set an alarm", "set alarm", 
        "alarm", "wake me up", "wake me"
    ]
    for phrase in action_phrases:
        temp_text = temp_text.replace(phrase, "")

    temp_text = re.sub(r"\s+", " ", temp_text).strip()

    connecting_words = ["with message", "saying", "because", "that", "about", "to", "for", "at", "in", "on"]
    changed = True
    while changed:
        changed = False
        for word in connecting_words:
            if temp_text.startswith(word + " "):
                temp_text = temp_text[len(word)+1:].strip()
                changed = True
            if temp_text.endswith(" " + word):
                temp_text = temp_text[:-len(word)-1].strip()
                changed = True
            if temp_text == word:
                temp_text = ""
                changed = True

    message = re.sub(r"\s+", " ", temp_text).strip()
    message = re.sub(r"^[,\s:-]+|[,\s:-]+$", "", message)

    return message if message and len(message) > 2 else "You have a reminder!"

def extract_message_absolute(command_text: str, time_str: str, target_time: datetime.datetime, is_reminder: bool) -> str:
    """Extracts the reminder content from an absolute time command."""
    temp_text = command_text.lower()
    temp_text = temp_text.replace(time_str, "")

    date_patterns = [
        r"\b(?:this|next)?\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(?:tomorrow|today|tonight)\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b",
        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b"
    ]
    for pattern in date_patterns:
        temp_text = re.sub(pattern, "", temp_text, flags=re.IGNORECASE)

    action_phrases = [
        "set a reminder", "set reminder", "reminder", "remind me", 
        "remember", "don't forget", "set an alarm", "set alarm", 
        "alarm", "wake me up", "wake me"
    ]
    for phrase in action_phrases:
        temp_text = temp_text.replace(phrase, "")

    temp_text = re.sub(r"\s+", " ", temp_text).strip()

    connecting_words = ["with message", "saying", "because", "that", "about", "to", "for", "at", "in", "on"]
    changed = True
    while changed:
        changed = False
        for word in connecting_words:
            if temp_text.startswith(word + " "):
                temp_text = temp_text[len(word)+1:].strip()
                changed = True
            if temp_text.endswith(" " + word):
                temp_text = temp_text[:-len(word)-1].strip()
                changed = True
            if temp_text == word:
                temp_text = ""
                changed = True

    message = re.sub(r"\s+", " ", temp_text).strip()
    message = re.sub(r"^[,\s:-]+|[,\s:-]+$", "", message)

    default_msg = "You have a reminder!" if is_reminder else "Time's up!"
    return message if message and len(message) > 2 and not message.isdigit() else default_msg

def parse_relative_time(command_text: str) -> Optional[Tuple[datetime.datetime, str]]:
    """Parses commands like 'remind me in 10 minutes'."""
    command_lower = command_text.lower()
    
    duration_minutes = parse_duration(command_lower)
    if duration_minutes:
        target_time = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)
        message = extract_reminder_message_simple(command_lower, duration_minutes)
        return target_time, message

    return None, None

def parse_absolute_time(command_text: str, is_reminder: bool = False) -> Optional[Tuple[datetime.datetime, str]]:
    """Parses commands with specific times like 'remind me at 5pm'."""
    command_lower = command_text.lower()
    now = datetime.datetime.now()

    time_match = re.search(r"(\d{1,2}:\d{2}(?:\s*[ap]\.?m\.?)?|\d{3,4}(?:\s*[ap]\.?m\.?)?|\d{1,2}(?:\s*[ap]\.?m\.?)?|noon|midnight|midday)", command_lower)
    if not time_match:
        return None, None

    time_str = time_match.group(1)
    parsed_time = parse_time(time_str)
    if not parsed_time:
        return None, None

    hour, minute = parsed_time
    target_date = now.date()

    if "tomorrow" in command_lower:
        target_date += datetime.timedelta(days=1)

    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(days_of_week):
        if day in command_lower:
            current_weekday = now.weekday()
            days_ahead = i - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            target_date += datetime.timedelta(days=days_ahead)
            break

    months = [
        "january", "february", "march", "april", "may", "june", 
        "july", "august", "september", "october", "november", "december"
    ]

    for i, month_name in enumerate(months, 1):
        pattern = rf"(?:{month_name}\s+(\d+)(?:st|nd|rd|th)?|(\d+)(?:st|nd|rd|th)?\s+(?:of\s+)?{month_name})"
        match = re.search(pattern, command_lower)
        if match:
            target_day_val = int(match.group(1) or match.group(2))
            try:
                target_date = datetime.date(now.year, i, target_day_val)
                if target_date < now.date():
                    target_date = datetime.date(now.year + 1, i, target_day_val)
                break
            except ValueError as e:
                print(f"Error creating date: {e}")
                return None, None

    try:
        target_datetime = datetime.datetime.combine(target_date, datetime.time(hour, minute))
    except ValueError as e:
        print(f"Error creating datetime: {e}")
        return None, None

    if (
        target_datetime <= now
        and "tomorrow" not in command_lower
        and not any(day in command_lower for day in days_of_week)
        and not any(month in command_lower for month in months)
    ):
        target_datetime += datetime.timedelta(days=1)

    message = extract_message_absolute(command_lower, time_str, target_datetime, is_reminder)
    return target_datetime, message
