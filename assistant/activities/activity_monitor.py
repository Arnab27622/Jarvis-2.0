import time
import threading
from assistant.core.speak_selector import speak


class ActivityMonitor:
    """
    A monitor that tracks user inactivity and offers assistance after periods of inactivity.

    The monitor operates in three phases:
    1. Initial delay period - no monitoring occurs
    2. Active monitoring - tracks time since last user activity
    3. Confirmation phase - asks user if they want advice after prolonged inactivity

    Attributes:
        initial_delay (int): Seconds to wait before starting monitoring
        check_interval (int): Seconds between inactivity checks
        inactivity_threshold (int): Seconds of inactivity before offering assistance
        last_activity_time (float): Timestamp of last recorded activity
        is_active (bool): Whether user is currently active
        monitor_thread (threading.Thread): Background monitoring thread
        stop_signal (bool): Signal to stop the monitoring thread
        initial_delay_passed (bool): Whether initial delay period has completed
        awaiting_confirmation (bool): Whether waiting for user response to offer
        confirmation_response (bool): User's response to assistance offer
        confirmation_start_time (float): Timestamp when confirmation was requested
        confirm_phrases (list): Phrases that indicate user accepts assistance
        decline_phrases (list): Phrases that indicate user declines assistance
    """

    def __init__(self, initial_delay=100, check_interval=120, inactivity_threshold=180):
        """
        Initialize the activity monitor with timing parameters.

        Args:
            initial_delay (int): Seconds before monitoring starts (default: 100)
            check_interval (int): Seconds between inactivity checks (default: 120)
            inactivity_threshold (int): Seconds of inactivity before offering help (default: 180)
        """
        self.initial_delay = initial_delay
        self.check_interval = check_interval
        self.inactivity_threshold = inactivity_threshold
        self.last_activity_time = time.time()
        self.is_active = False
        self.monitor_thread = None
        self.stop_signal = False
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

        # Start initial delay timer
        threading.Timer(self.initial_delay, self._set_initial_delay_passed).start()

    def _set_initial_delay_passed(self):
        """Mark that the initial delay has passed and monitoring can begin."""
        self.initial_delay_passed = True

    def record_activity(self):
        """Record user activity and update last activity timestamp."""
        self.last_activity_time = time.time()
        self.is_active = True
        # Don't reset awaiting_confirmation here as it interferes with confirmation handling

    def start_monitoring(self):
        """Start the inactivity monitoring thread."""
        if self.monitor_thread is None:
            self.stop_signal = False
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop the inactivity monitoring thread."""
        self.stop_signal = True
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None

    def is_confirmation_response(self, text):
        """
        Check if the given text is a response to the confirmation prompt.

        Args:
            text (str): The text to check for confirmation response

        Returns:
            bool: True if text matches confirmation or decline phrases, False otherwise
        """
        if not self.awaiting_confirmation:
            return False

        text_lower = text.lower()

        # Check for positive responses
        if any(phrase in text_lower for phrase in self.confirm_phrases):
            return True

        # Check for negative responses
        elif any(phrase in text_lower for phrase in self.decline_phrases):
            return True

        return False

    def handle_confirmation_response(self, text):
        """
        Process a user's response to the confirmation prompt.

        Args:
            text (str): User's response text

        Returns:
            bool or None: True if user accepts, False if user declines, None if no match
        """
        if not self.awaiting_confirmation:
            return None

        text_lower = text.lower()

        # Check for positive responses
        if any(phrase in text_lower for phrase in self.confirm_phrases):
            self.awaiting_confirmation = False
            return True

        # Check for negative responses
        elif any(phrase in text_lower for phrase in self.decline_phrases):
            self.awaiting_confirmation = False
            speak("Okay, let me know if you need anything.")
            return False

        # If response doesn't match, return None
        return None

    def ask_for_confirmation(self):
        """Ask the user if they want assistance after period of inactivity."""
        self.awaiting_confirmation = True
        self.confirmation_start_time = time.time()
        speak("You've been idle for a while. Would you like some advice?")

    def check_confirmation_timeout(self):
        """
        Check if confirmation timeout has been reached (6 seconds).

        Returns:
            bool: True if timeout reached, False otherwise
        """
        if (
            self.awaiting_confirmation
            and time.time() - self.confirmation_start_time > 6
        ):
            self.awaiting_confirmation = False
            return True
        return False

    def reset_confirmation_state(self):
        """Reset the confirmation state when returning to normal command listening."""
        self.awaiting_confirmation = False
        self.confirmation_response = None
        self.confirmation_start_time = 0

    def _monitor_loop(self):
        """
        Main monitoring loop that runs in background thread.

        Continuously checks for user inactivity and manages the confirmation process.
        """
        while not self.stop_signal:
            time.sleep(self.check_interval)

            # Don't check until initial delay has passed
            if not self.initial_delay_passed:
                continue

            # Check for confirmation timeout
            if self.check_confirmation_timeout():
                continue

            current_time = time.time()
            time_since_last_activity = current_time - self.last_activity_time

            # Check if user is inactive beyond threshold and not already awaiting confirmation
            if (
                time_since_last_activity >= self.inactivity_threshold
                and not self.is_active
                and not self.awaiting_confirmation
            ):
                # Ask for confirmation before giving advice
                self.ask_for_confirmation()

            # Update activity status
            self.is_active = False


# Global instance
activity_monitor = ActivityMonitor()


def start_activity_monitoring():
    """Start the global activity monitoring system."""
    activity_monitor.start_monitoring()


def stop_activity_monitoring():
    """Stop the global activity monitoring system."""
    activity_monitor.stop_monitoring()


def record_user_activity():
    """Record user activity in the global activity monitor."""
    activity_monitor.record_activity()
