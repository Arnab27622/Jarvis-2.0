"""
Module for monitoring system battery status and hardware telemetry.
Provides background threads for voice alerts, state change detection, and system metrics.
"""

import psutil
import time
import random
import threading
from typing import Optional
from assistant.core.speak_selector import speak
from data.dlg_data.dlg import last_low, low_b, full_battery, plug_in, plug_out
from assistant.core.event_bus import bus, EventType


class BatteryMonitor:
    """
    Manages battery status tracking and system resource telemetry.

    Handles background monitoring of battery levels, power connection states,
    and system performance metrics (CPU/RAM), emitting events via the EventBus.
    """

    def __init__(self):
        """Initializes the monitor with default state and thread control."""
        self.previous_plugged_state = None
        self.stop_event = threading.Event()
        self.alert_thread = None
        self.plugin_thread = None

    def get_battery_info(self) -> Optional[tuple]:
        """
        Retrieves current battery percentage and power status.

        Returns:
            Optional[tuple]: (percentage, power_plugged) or None if unavailable.
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
        Monitors battery levels and triggers voice alerts for critical thresholds.

        Args:
            check_interval (int): Seconds between checks.
        """
        self.stop_event.clear()
        notified_full = False

        while not self.stop_event.is_set():
            battery_info = self.get_battery_info()
            if battery_info is None:
                if self.stop_event.wait(60):
                    break
                continue

            percent, plugged = battery_info
            bus.emit(EventType.BATTERY_UPDATE, {"percent": percent, "plugged": plugged})

            if percent < 10:
                speak(random.choice(last_low))
            elif percent < 30:
                speak(random.choice(low_b))
            elif percent == 100 and plugged and not notified_full:
                speak(random.choice(full_battery))
                notified_full = True
            elif percent < 95:
                notified_full = False

            if self.stop_event.wait(check_interval):
                break

    def check_plugin_status(self, check_interval: int = 5) -> None:
        """
        Monitors power connection status and triggers voice alerts on changes.

        Args:
            check_interval (int): Seconds between checks.
        """
        self.stop_event.clear()

        battery_info = self.get_battery_info()
        if battery_info:
            self.previous_plugged_state = battery_info[1]

        while not self.stop_event.is_set():
            battery_info = self.get_battery_info()
            if battery_info is None:
                if self.stop_event.wait(check_interval):
                    break
                continue

            percent, plugged = battery_info
            bus.emit(EventType.BATTERY_UPDATE, {"percent": percent, "plugged": plugged})

            if plugged != self.previous_plugged_state:
                if plugged:
                    speak(random.choice(plug_in))
                else:
                    speak(random.choice(plug_out))
                self.previous_plugged_state = plugged

            if self.stop_event.wait(check_interval):
                break

    def battery_percentage(self) -> None:
        """Reports current battery status via voice."""
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
        """Starts background threads for battery and telemetry monitoring."""
        self.stop_monitoring()

        self.stop_event.clear()
        self.alert_thread = threading.Thread(target=self.battery_alert, daemon=True)
        self.plugin_thread = threading.Thread(
            target=self.check_plugin_status, daemon=True
        )
        self.telemetry_thread = threading.Thread(
            target=self.emit_telemetry, daemon=True
        )

        self.alert_thread.start()
        self.plugin_thread.start()
        self.telemetry_thread.start()
        print("Battery & Telemetry monitoring started")

    def stop_monitoring(self) -> None:
        """Stops all background monitoring threads."""
        self.stop_event.set()
        if self.alert_thread and self.alert_thread.is_alive():
            self.alert_thread.join(timeout=2)
        if self.plugin_thread and self.plugin_thread.is_alive():
            self.plugin_thread.join(timeout=2)
        if hasattr(self, 'telemetry_thread') and self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=2)
        print("Battery & Telemetry monitoring stopped")


    def emit_telemetry(self) -> None:
        """Continuously emits CPU and RAM metrics to the EventBus."""
        self.stop_event.clear()
        
        while not self.stop_event.is_set():
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            bus.emit(EventType.SYS_METRICS, {
                "cpu": cpu,
                "ram": ram
            })
            
            if self.stop_event.wait(2.0):
                break

battery_monitor = BatteryMonitor()

if __name__ == "__main__":
    battery_monitor.battery_percentage()
    battery_monitor.start_monitoring()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        battery_monitor.stop_monitoring()
