import psutil
import time
import random
import threading
from typing import Optional
from assistant.core.speak_selector import speak
from data.dlg_data.dlg import last_low, low_b, full_battery, plug_in, plug_out


class BatteryMonitor:
    """
    A battery monitoring system that tracks battery percentage and power connection status.

    This class provides real-time monitoring of battery levels and power plug status,
    with automated alerts for low battery, full charge, and plug state changes.

    Features:
    - Battery percentage monitoring with tiered alerts
    - Power plug connection/disconnection detection
    - Background monitoring with configurable intervals
    - Thread-safe operations with start/stop control

    Attributes:
        previous_plugged_state (bool): Tracks the last known power plug status
        monitoring (bool): Flag indicating if monitoring is active
        alert_thread (threading.Thread): Thread for battery level monitoring
        plugin_thread (threading.Thread): Thread for plug status monitoring
    """

    def __init__(self):
        """Initialize the battery monitor with default state."""
        self.previous_plugged_state = None
        self.monitoring = False
        self.alert_thread = None
        self.plugin_thread = None

    def get_battery_info(self) -> Optional[tuple]:
        """
        Safely retrieve battery information with comprehensive error handling.

        Uses psutil to get battery status and handles cases where battery
        information might not be available (desktop computers, virtual environments).

        Returns:
            Optional[tuple]: A tuple containing (percentage, power_plugged) where:
                - percentage (int): Battery charge percentage (0-100)
                - power_plugged (bool): True if AC power is connected
            Returns None if battery information is unavailable or an error occurs.

        Raises:
            Exception: Logs any exceptions but returns None to maintain system stability
        """
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return None
            return int(battery.percent), battery.power_plugged
        except Exception as e:
            print(f"Error getting battery info: {e}")
            return None

    def battery_alert(self, check_interval: int = 300) -> None:
        """
        Monitor battery level and provide voice alerts for critical states.

        Continuously checks battery percentage and provides alerts for:
        - Critical low battery (<10%)
        - Low battery (<30%)
        - Full battery (100% while plugged in)

        The full battery notification is only given once per charge cycle
        and resets when battery drops below 95%.

        Args:
            check_interval (int): Seconds between battery checks (default: 300/5 minutes)
        """
        self.monitoring = True
        notified_full = False  # Track if full battery notification was given

        while self.monitoring:
            battery_info = self.get_battery_info()
            if battery_info is None:
                time.sleep(60)  # Wait longer if battery info unavailable
                continue

            percent, plugged = battery_info

            # Tiered alert system based on battery level
            if percent < 10:
                speak(random.choice(last_low))  # Critical low battery
            elif percent < 30:
                speak(random.choice(low_b))  # Low battery warning
            elif percent == 100 and plugged and not notified_full:
                speak(random.choice(full_battery))  # Full charge notification
                notified_full = True
            elif percent < 95:
                # Reset full notification when battery drops below 95%
                notified_full = False

            time.sleep(check_interval)

    def check_plugin_status(self, check_interval: int = 5) -> None:
        """
        Monitor power plug connection status changes.

        Detects when the device is plugged in or unplugged from AC power
        and provides voice notifications for state changes.

        Args:
            check_interval (int): Seconds between plug status checks (default: 5)
        """
        self.monitoring = True

        # Get initial state to detect changes
        battery_info = self.get_battery_info()
        if battery_info:
            self.previous_plugged_state = battery_info[1]

        while self.monitoring:
            battery_info = self.get_battery_info()
            if battery_info is None:
                time.sleep(check_interval)
                continue

            percent, plugged = battery_info

            # Only speak if plug state has changed
            if plugged != self.previous_plugged_state:
                if plugged:
                    speak(random.choice(plug_in))  # Device plugged in
                else:
                    speak(random.choice(plug_out))  # Device unplugged
                self.previous_plugged_state = plugged

            time.sleep(check_interval)

    def battery_percentage(self) -> None:
        """
        Report current battery status via voice.

        Provides a comprehensive battery status report including:
        - Current battery percentage
        - Power connection status (plugged in or on battery)

        Handles cases where battery information is unavailable.
        """
        battery_info = self.get_battery_info()
        if battery_info:
            percent, plugged = battery_info
            status = "plugged in" if plugged else "on battery power"
            speak(
                f"The device is running on {percent}% battery, and is currently {status}."
            )
        else:
            speak("Sorry, I couldn't retrieve the battery information.")

    def start_monitoring(self) -> None:
        """
        Start background battery monitoring in separate threads.

        Initializes and starts two monitoring threads:
        1. Battery level alerts (5-minute intervals)
        2. Power plug status (5-second intervals)

        Stops any existing monitoring before starting new threads to prevent duplicates.
        """
        self.stop_monitoring()  # Stop any existing monitoring

        self.monitoring = True
        self.alert_thread = threading.Thread(target=self.battery_alert, daemon=True)
        self.plugin_thread = threading.Thread(
            target=self.check_plugin_status, daemon=True
        )

        self.alert_thread.start()
        self.plugin_thread.start()
        print("Battery monitoring started")

    def stop_monitoring(self) -> None:
        """
        Stop all battery monitoring activities.

        Safely stops both monitoring threads with timeout protection
        to prevent thread hanging during shutdown.
        """
        self.monitoring = False
        if self.alert_thread and self.alert_thread.is_alive():
            self.alert_thread.join(timeout=2)
        if self.plugin_thread and self.plugin_thread.is_alive():
            self.plugin_thread.join(timeout=2)
        print("Battery monitoring stopped")


# Create a global instance for easy access across the application
battery_monitor = BatteryMonitor()

if __name__ == "__main__":
    """
    Demonstration of BatteryMonitor functionality when run as a standalone script.

    Usage example:
    1. Reports current battery status
    2. Starts continuous monitoring
    3. Runs until interrupted with Ctrl+C
    """
    # Example usage
    battery_monitor.battery_percentage()
    battery_monitor.start_monitoring()

    try:
        # Keep the main thread alive while monitoring runs in background
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        battery_monitor.stop_monitoring()
