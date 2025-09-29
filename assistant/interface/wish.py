import datetime
import random
from data.dlg_data.dlg import *
from assistant.core.speak_selector import speak

today = datetime.date.today()
formatted_date = today.strftime("%d %b %y")
nowx = datetime.datetime.now()


def wish():
    current_hour = nowx.hour
    if 5 <= current_hour < 12:
        gm_dlg = random.choice(good_morningdlg)
        speak(gm_dlg)
    elif 12 <= current_hour < 17:
        ga_dlg = random.choice(good_afternoondlg)
        speak(ga_dlg)
    elif 17 <= current_hour < 21:
        ge_dlg = random.choice(good_eveningdlg)
        speak(ge_dlg)
    else:
        gn_dlg = random.choice(good_nightdlg)
        speak(gn_dlg)


if __name__ == "__main__":
    wish()
