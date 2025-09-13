from function.wish import wish
import sys
import random
from pathlib import Path
from function.commands import command


current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from data.dlg_data.dlg import (
    offline_dlg,
    online_dlg,
)
from function.check_status import is_online
from friday.fspeak import fspeak
from friday.f2speak import f2speak
from function.activity_monitor import (
    stop_activity_monitoring,
)


def jarvis():
    wish()

    command()


if __name__ == "__main__":
    try:
        if is_online():
            # f2speak(random.choice(online_dlg))
            # f2speak("Initializing JARVIS")
            jarvis()
        else:
            fspeak(random.choice(offline_dlg))
    except KeyboardInterrupt:
        stop_activity_monitoring()
        print("\nJARVIS shutting down...")
    except Exception as e:
        stop_activity_monitoring()
        print(f"An error occurred: {e}")
