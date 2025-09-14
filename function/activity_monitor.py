import time
import threading
from pathlib import Path
import sys

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from head.speak_selector import speak


class ActivityMonitor:
    def __init__(self, initial_delay=80, check_interval=40, inactivity_threshold=100):
        """
        Initialize the activity monitor
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
        """Mark that the initial delay has passed"""
        self.initial_delay_passed = True

    def record_activity(self):
        """Call this whenever there's user activity"""
        self.last_activity_time = time.time()
        self.is_active = True
        # Don't reset awaiting_confirmation here as it interferes with confirmation handling

    def start_monitoring(self):
        """Start the inactivity monitoring thread"""
        if self.monitor_thread is None:
            self.stop_signal = False
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop the inactivity monitoring"""
        self.stop_signal = True
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None

    def is_confirmation_response(self, text):
        """Check if the text is a response to the confirmation prompt"""
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
        """Handle a response to the confirmation prompt"""
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
        """Ask user if they want advice"""
        self.awaiting_confirmation = True
        self.confirmation_start_time = time.time()
        speak("You've been idle for a while. Would you like some advice?")

    def check_confirmation_timeout(self):
        """Check if confirmation timeout has been reached"""
        if (
            self.awaiting_confirmation
            and time.time() - self.confirmation_start_time > 5
        ):
            self.awaiting_confirmation = False
            return True
        return False

    def _monitor_loop(self):
        """Main monitoring loop"""
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
    """Start the activity monitoring system"""
    activity_monitor.start_monitoring()


def stop_activity_monitoring():
    """Stop the activity monitoring system"""
    activity_monitor.stop_monitoring()


def record_user_activity():
    """Call this function whenever there's user interaction"""
    activity_monitor.record_activity()
