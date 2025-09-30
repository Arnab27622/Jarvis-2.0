from assistant.core.speak_selector import speak
import datetime


def tell_time():
    """
    Announce the current system time in a natural, spoken format.

    Retrieves the current time from the system clock and formats it for
    clear verbal communication. Uses 12-hour format with AM/PM designation
    for intuitive understanding.

    Time Format:
        - %I: Hour in 12-hour format (01-12)
        - %M: Minute with leading zeros (00-59)
        - %p: AM/PM designation

    Example Output:
        - "The current time is 02:30 PM"
        - "The current time is 09:15 AM"

    Note:
        The function uses the system's local timezone and clock settings.
        Ensure the system time is correctly set for accurate reporting.

    Usage:
        >>> tell_time()
        # Speaks: "The current time is 02:30 PM"
    """
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The current time is {current_time}")


def tell_date():
    """
    Announce the current system date in a comprehensive, spoken format.

    Retrieves the current date from the system clock and formats it as
    a complete date string including day of week, month, day, and year
    for clear verbal communication.

    Date Format:
        - %A: Full weekday name (e.g., Monday, Tuesday)
        - %B: Full month name (e.g., January, February)
        - %d: Day of the month with leading zeros (01-31)
        - %Y: Four-digit year (e.g., 2024)

    Example Output:
        - "Today is Monday, January 15, 2024"
        - "Today is Friday, December 25, 2024"

    Note:
        The function uses the system's local timezone and date settings.
        The output follows standard English date conventions.

    Usage:
        >>> tell_date()
        # Speaks: "Today is Monday, January 15, 2024"
    """
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today is {current_date}")
