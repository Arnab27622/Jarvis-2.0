from pathlib import Path
import sys
import psutil
import time
import random
import threading
from typing import Optional

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))


from head.speak_selector import speak
from data.dlg_data.dlg import last_low, low_b, full_battery, plug_in, plug_out


class BatteryMonitor:
    def __init__(self):
        self.previous_plugged_state = None
        self.monitoring = False
        self.alert_thread = None
        self.plugin_thread = None

    def get_battery_info(self) -> Optional[tuple]:
        """Safely get battery information with error handling"""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return None
            return int(battery.percent), battery.power_plugged
        except Exception as e:
            print(f"Error getting battery info: {e}")
            return None

    def battery_alert(self, check_interval: int = 300) -> None:
        """Monitor battery level and provide alerts"""
        self.monitoring = True
        notified_full = False

        while self.monitoring:
            battery_info = self.get_battery_info()
            if battery_info is None:
                time.sleep(60)  # Wait longer if battery info unavailable
                continue

            percent, plugged = battery_info

            if percent < 10:
                speak(random.choice(last_low))
            elif percent < 30:
                speak(random.choice(low_b))
            elif percent == 100 and plugged and not notified_full:
                speak(random.choice(full_battery))
                notified_full = True
            elif percent < 95:
                notified_full = (
                    False  # Reset full notification when battery drops below 95%
                )

            time.sleep(check_interval)

    def check_plugin_status(self, check_interval: int = 5) -> None:
        """Monitor power plug status changes"""
        self.monitoring = True

        # Get initial state
        battery_info = self.get_battery_info()
        if battery_info:
            self.previous_plugged_state = battery_info[1]

        while self.monitoring:
            battery_info = self.get_battery_info()
            if battery_info is None:
                time.sleep(check_interval)
                continue

            percent, plugged = battery_info

            # Only speak if state has changed
            if plugged != self.previous_plugged_state:
                if plugged:
                    speak(random.choice(plug_in))
                else:
                    speak(random.choice(plug_out))
                self.previous_plugged_state = plugged

            time.sleep(check_interval)

    def battery_percentage(self) -> None:
        """Report current battery percentage"""
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
        """Start battery monitoring in background threads"""
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
        """Stop all battery monitoring"""
        self.monitoring = False
        if self.alert_thread and self.alert_thread.is_alive():
            self.alert_thread.join(timeout=2)
        if self.plugin_thread and self.plugin_thread.is_alive():
            self.plugin_thread.join(timeout=2)
        print("Battery monitoring stopped")


# Create a global instance
battery_monitor = BatteryMonitor()

if __name__ == "__main__":
    # Example usage
    battery_monitor.battery_percentage()
    battery_monitor.start_monitoring()

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        battery_monitor.stop_monitoring()
