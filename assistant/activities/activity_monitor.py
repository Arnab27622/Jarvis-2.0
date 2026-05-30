"""
Module for monitoring user inactivity and proactively offering assistance.
"""

import time
import threading
from assistant.core.speak_selector import speak
from assistant.core.event_bus import bus, EventType


class ActivityMonitor:
    """
    Tracks user inactivity and manages proactive assistance prompts.

    Attributes:
        initial_delay (int): Seconds to wait before starting monitoring.
        check_interval (int): Seconds between inactivity checks.
        inactivity_threshold (int): Seconds of inactivity before offering help.
        last_activity_time (float): Timestamp of last recorded activity.
        is_active (bool): Current activity status.
        monitor_thread (threading.Thread): Background thread for monitoring.
        stop_event (threading.Event): Signal to terminate the monitor thread.
        initial_delay_passed (bool): Flag indicating initial delay completion.
        awaiting_confirmation (bool): Flag indicating a pending user response.
        confirm_phrases (list): Phrases triggering positive assistance response.
        decline_phrases (list): Phrases triggering negative assistance response.
    """

    def __init__(self, initial_delay: int = 100, check_interval: int = 120, inactivity_threshold: int = 180) -> None:
        """
        Initializes the monitor with timing configurations.
        """
        self.initial_delay = initial_delay
        self.check_interval = check_interval
        self.inactivity_threshold = inactivity_threshold
        self.last_activity_time = time.time()
        self.is_active = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.initial_delay_passed = False
        self.awaiting_confirmation = False
        self.confirmation_response = None
        self.confirmation_start_time = 0

        # Confirmation phrases
        self.confirm_phrases = [
            "yes please",
            "give advice",
            "sure thing",
            "go ahead",
            "yes jarvis",
        ]

        self.decline_phrases = [
            "no thanks",
            "not now",
            "maybe later",
            "no jarvis",
            "skip it",
        ]

        threading.Timer(self.initial_delay, self._set_initial_delay_passed).start()

    def _set_initial_delay_passed(self) -> None:
        """Sets the flag indicating the initial delay period has elapsed."""
        self.initial_delay_passed = True

    def record_activity(self) -> None:
        """Updates the last activity timestamp and sets active status."""
        self.last_activity_time = time.time()
        self.is_active = True

    def start_monitoring(self) -> None:
        """Initializes and starts the background monitoring thread."""
        if self.monitor_thread is None:
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Signals the monitoring thread to stop and joins it."""
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None

    def is_confirmation_response(self, text: str) -> bool:
        """Checks if the provided text matches a valid confirmation or decline phrase."""
        if not self.awaiting_confirmation:
            return False

        text_lower = text.lower()

        if any(phrase in text_lower for phrase in self.confirm_phrases):
            return True

        elif any(phrase in text_lower for phrase in self.decline_phrases):
            return True

        return False

    def handle_confirmation_response(self, text: str) -> bool | None:
        """Processes user input to determine if they accept or decline assistance."""
        if not self.awaiting_confirmation:
            return None

        text_lower = text.lower()

        if any(phrase in text_lower for phrase in self.confirm_phrases):
            self.awaiting_confirmation = False
            return True

        elif any(phrase in text_lower for phrase in self.decline_phrases):
            self.awaiting_confirmation = False
            speak("Okay, let me know if you need anything.")
            return False

        return None

    def ask_for_confirmation(self) -> None:
        """Triggers the assistance prompt and sets the confirmation state."""
        self.awaiting_confirmation = True
        self.confirmation_start_time = time.time()
        msg = "You've been idle for a while. Would you like some advice?"
        speak(msg)
        bus.emit(EventType.NOTIFY, {"text": msg, "timestamp": time.time()})

    def check_confirmation_timeout(self) -> bool:
        """Checks if the confirmation window has expired."""
        if (
            self.awaiting_confirmation
            and time.time() - self.confirmation_start_time > 6
        ):
            self.awaiting_confirmation = False
            return True
        return False

    def reset_confirmation_state(self) -> None:
        """Clears the current confirmation state."""
        self.awaiting_confirmation = False
        self.confirmation_response = None
        self.confirmation_start_time = 0

    def _monitor_loop(self) -> None:
        """Background loop that evaluates inactivity and manages prompts."""
        while not self.stop_event.is_set():
            if self.stop_event.wait(self.check_interval):
                break

            if not self.initial_delay_passed:
                continue

            if self.check_confirmation_timeout():
                continue

            current_time = time.time()
            time_since_last_activity = current_time - self.last_activity_time

            if (
                time_since_last_activity >= self.inactivity_threshold
                and not self.is_active
                and not self.awaiting_confirmation
            ):
                self.ask_for_confirmation()

            self.is_active = False


activity_monitor = ActivityMonitor()


def start_activity_monitoring():
    """Starts the global activity monitor."""
    activity_monitor.start_monitoring()


def stop_activity_monitoring():
    """Stops the global activity monitor."""
    activity_monitor.stop_monitoring()


def record_user_activity():
    """Registers user activity with the global monitor."""
    activity_monitor.record_activity()
