import datetime
import threading
from assistant.interface.wish import wish
import random
from assistant.interface.commands import command
from data.dlg_data.dlg import (
    offline_dlg,
    online_dlg,
)
from assistant.activities.check_status import is_online
from assistant.secondary_tts.fspeak import fspeak
from assistant.secondary_tts.f2speak import f2speak
from assistant.activities.activity_monitor import stop_activity_monitoring
from assistant.activities.battery_features import battery_monitor
from assistant.automation.integrations.alarm_reminder import (
    load_alarms,
    load_reminders,
    active_alarms,
    active_reminders,
    alarm_worker,
    reminder_worker,
    alarm_threads,
    reminder_threads,
    save_alarms,
    save_reminders,
)


def restore_alarms_and_reminders_on_startup():
    """Restore alarms and reminders after system restart"""
    try:
        load_alarms()
        load_reminders()
        current_time = datetime.datetime.now()

        # Restore alarms
        for alarm_id, alarm_data in list(active_alarms.items()):
            try:
                alarm_time = datetime.datetime.fromisoformat(alarm_data["time"])
                if alarm_time > current_time:
                    # Alarm is still in the future, restart it
                    message = alarm_data.get("message", "")
                    thread = threading.Thread(
                        target=alarm_worker, args=(alarm_id, alarm_time, message)
                    )
                    thread.daemon = True
                    thread.start()
                    alarm_threads[alarm_id] = thread
                else:
                    # Alarm time has passed, remove it
                    del active_alarms[alarm_id]
            except Exception as e:
                print(f"Error restoring alarm {alarm_id}: {e}")
                # Remove corrupted alarm
                if alarm_id in active_alarms:
                    del active_alarms[alarm_id]

        # Restore reminders
        for reminder_id, reminder_data in list(active_reminders.items()):
            try:
                reminder_time = datetime.datetime.fromisoformat(reminder_data["time"])
                if reminder_time > current_time:
                    # Reminder is still in the future, restart it
                    message = reminder_data.get("message", "")
                    thread = threading.Thread(
                        target=reminder_worker,
                        args=(reminder_id, reminder_time, message),
                    )
                    thread.daemon = True
                    thread.start()
                    reminder_threads[reminder_id] = thread
                else:
                    # Reminder time has passed, remove it
                    del active_reminders[reminder_id]
            except Exception as e:
                print(f"Error restoring reminder {reminder_id}: {e}")
                # Remove corrupted reminder
                if reminder_id in active_reminders:
                    del active_reminders[reminder_id]

        # Save cleaned up data
        save_alarms()
        save_reminders()

        print("Alarms and reminders restored on startup")

    except Exception as e:
        print(f"Error restoring alarms and reminders: {e}")


def jarvis():
    wish()
    restore_alarms_and_reminders_on_startup()
    battery_monitor.start_monitoring()
    command()


if __name__ == "__main__":
    try:
        if is_online():
            f2speak(random.choice(online_dlg))
            f2speak("Initializing JARVIS...")
            jarvis()
        else:
            fspeak(random.choice(offline_dlg))
    except KeyboardInterrupt:
        stop_activity_monitoring()
        battery_monitor.stop_monitoring()
        print("\nJARVIS shutting down...")
    except Exception as e:
        stop_activity_monitoring()
        battery_monitor.stop_monitoring()
        print(f"An error occurred: {e}")
        print("JARVIS shutting down due to error...")