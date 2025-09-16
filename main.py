from assistant.interface.wish import wish
import sys
import random
from pathlib import Path
from assistant.interface.commands import command


current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from data.dlg_data.dlg import (
    offline_dlg,
    online_dlg,
)
from assistant.activities.check_status import is_online
from assistant.secondary_tts.fspeak import fspeak
from assistant.secondary_tts.f2speak import f2speak
from assistant.activities.activity_monitor import (
    stop_activity_monitoring,
)
from assistant.activities.battery_features import battery_monitor


def jarvis():
    wish()
    battery_monitor.start_monitoring()
    command()


if __name__ == "__main__":
    try:
        if is_online():
            f2speak(random.choice(online_dlg))
            f2speak("Initializing JARVIS")
            jarvis()
        else:
            fspeak(random.choice(offline_dlg))
    except KeyboardInterrupt:
        stop_activity_monitoring()
        battery_monitor.start_monitoring()
        print("\nJARVIS shutting down...")
    except Exception as e:
        stop_activity_monitoring()
        battery_monitor.start_monitoring()
        print(f"An error occurred: {e}")
