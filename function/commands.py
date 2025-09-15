from function.welcome import welcome
from function.advice import rand_advice
from function.activity_monitor import *
from automation.features.window_automation import *
from automation.features.utility_automation import *
from automation.features.location_automation import get_current_location, check_ip_address
from automation.features.google_search_automation import handle_web_search
from automation.features.task_schedule_automation import recall_info, remember_info
from automation.features.jokes_automation import tell_joke
from automation.features.datetime_automation import tell_date, tell_time
from automation.features.internet_speed import check_internet_speed
from automation.features.youtube_automation import *
from head.ear import listen
from head.brain import brain
from automation.open import open_command
from automation.close import close_command
from automation.battery_features import battery_monitor
from data.dlg_data.dlg import *
import random
import re
import pyautogui as ui
import os
import time


def wait_for_wakeword():
    """
    Wait for the hotword/wake word to be spoken.
    Returns True once detected to start listening,
    Returns False if a close command is detected to exit loop.
    """
    speak("Awaiting your command...")
    while True:
        text = listen()
        if text is None:
            continue

        text_lower = text.lower().strip()

        if any(keyword.strip() == text_lower for keyword in wakeup_key_word):
            welcome()
            return True

        if any(keyword in text_lower for keyword in bye_key_word):
            response = random.choice(res_bye)
            speak(response)
            stop_activity_monitoring()
            return False

        # Otherwise ignore and keep waiting


def command():
    while True:
        start_activity_monitoring()

        # Wait for wake word first, or exit if closed
        if not wait_for_wakeword():
            break  # close command said, break the loop to exit

        # After wake word detected, listen for command
        text = listen()

        if text is None:
            print("Sorry, I couldn't understand. Please try again.")
            continue

        # Check if this is a response to the confirmation prompt FIRST
        if activity_monitor.awaiting_confirmation:
            # Handle the confirmation response
            result = activity_monitor.handle_confirmation_response(text)
            # If user confirmed, give advice
            if result is True:
                advice = rand_advice()
                if advice:
                    speak(advice)
            # Continue to next iteration regardless of result
            continue

        # Only record activity and process normally if not a confirmation response
        record_user_activity()

        text_lower = text.lower().strip()

        # Check bye keywords to exit
        if any(keyword in text_lower for keyword in bye_key_word):
            response = random.choice(res_bye)
            speak(response)
            stop_activity_monitoring()
            break

        process_command(text_lower)


def process_command(text):
    """Process command whether they contain 'jarvis' or not"""

    # Check if 'jarvis' is present and clean it out anyway
    if "jarvis" in text:
        text = re.sub(r"\bjarvis\b", "", text).strip()

    if not text:
        welcome()
        return

    first_word = text.split()[0] if text else ""

    if first_word in open_input:
        target = " ".join(text.split()[1:])
        open_command(target)

    elif first_word in close_input:
        close_command()

    elif (
        "minimize" in text
        or "minimise" in text
        or "minimise the window" in text
        or "minimize the window" in text
    ):
        handle_minimize()

    elif (
        "maximize" in text
        or "maximise" in text
        or "maximise the window" in text
        or "maximize the window" in text
    ):
        handle_maximize()

    elif "restore" in text or "restore window" in text:
        handle_restore()

    elif "switch window" in text or "next window" in text:
        handle_window_switch()

    elif "new tab" in text:
        ui.hotkey("ctrl", "t")
        speak("New tab opened")

    elif "incognito" in text or "private tab" in text:
        open_incognito_tab()

    elif "bookmark" in text or "bookmark this" in text:
        bookmark_page()

    elif "developer tools" in text or "dev tools" in text:
        open_dev_tools()

    elif "full screen" in text or "fullscreen" in text:
        toggle_fullscreen()

    elif "reload" in text or "refresh" in text:
        reload_page()

    elif "go back" in text or "back page" in text:
        go_back()

    elif "go forward" in text or "forward page" in text:
        go_forward()

    elif (
        "duplicate tab" in text
        or "duplicate the tab" in text
        or "duplicate this tab" in text
    ):
        duplicate_tab()

    elif "brightness" in text:
        handle_brightness(text)

    elif "write" in text or "right" in text:
        handle_write(text)

    elif "enter" in text or "press enter" in text:
        ui.press("enter")

    elif "select all" in text or "select all paragraph" in text:
        ui.hotkey("ctrl", "a")

    elif "cut" in text or "cut this" in text:
        ui.hotkey("ctrl", "x")

    elif "copy" in text or "copy this" in text:
        ui.hotkey("ctrl", "c")

    elif "paste" in text or "paste here" in text:
        ui.hotkey("ctrl", "v")

    elif "undo" in text or "undo it" in text:
        ui.hotkey("ctrl", "z")

    elif "redo" in text or "redo it" in text:
        ui.hotkey("ctrl", "y")

    elif "copy last paragraph" in text:
        ui.hotkey("ctrl", "shift", "c")

    elif "increase volume" in text or "increase the volume" in text:
        handle_volume_change("increase")

    elif "decrease volume" in text or "decrease the volume" in text:
        handle_volume_change("decrease")

    elif "unmute" in text:
        ui.hotkey("volumemute")
        speak("Volume unmuted")

    elif "mute" in text:
        speak("Muting volume")
        ui.press("volumemute")

    elif "screenshot" in text or "take screenshot" in text:
        take_screenshot()

    elif (
        "check internet speed" in text
        or "run speed test" in text
        or "check internet connection" in text
    ):
        check_internet_speed()

    elif "scroll up" in text or "scroll down" in text:
        handle_scroll(text)

    elif "scroll to top" in text or "scroll to the top" in text:
        handle_scroll_to_top()

    elif "scroll to bottom" in text or "scroll to the bottom" in text:
        handle_scroll_to_bottom()

    elif "page up" in text:
        speak("Scrolling page up")
        ui.press("pageup")

    elif "page down" in text:
        speak("Scrolling page down")
        ui.press("pagedown")

    elif "current location" in text or "where am i" in text:
        get_current_location()

    elif "play" in text and "youtube" in text:
        if "on youtube" in text:
            search_query = text.split("play")[1].split("on youtube")[0].strip()
        else:
            search_query = text.split("play")[1].replace("youtube", "").strip()
        play_on_youtube(search_query)

    elif "search for" in text and "youtube" in text:
        if "on youtube" in text:
            search_query = text.split("search for")[1].split("on youtube")[0].strip()
        else:
            search_query = text.split("search for")[1].replace("youtube", "").strip()
        search_on_youtube(search_query)

    elif "search" in text and "for" in text and "google" in text:
        handle_web_search(text)

    elif "what time" in text or "what's the time" in text or "what's the current time" in text:
        tell_time()

    elif "what date" in text or "what's the date" in text:
        tell_date()

    elif "tell a joke" in text or "tell me a joke" in text or "a joke" in text:
        tell_joke()

    elif "system info" in text or "system status" in text:
        get_system_info()

    elif "battery percentage" in text or "battery status" in text:
        battery_monitor.battery_percentage()

    elif "check ip address" in text or "check my ip address" in text:
        check_ip_address()

    elif "remember that" in text:
        remember_info(text)

    elif "what did i ask you to remember" in text:
        recall_info()

    elif "shutdown" in text:
        speak("Shutting down the system in 10 seconds")
        os.system("shutdown /s /t 10")

    elif "restart" in text:
        speak("Restarting the system in 10 seconds")
        os.system("shutdown /r /t 10")

    elif "sleep" in text:
        speak("Putting the system to sleep")
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    else:
        brain(text)
        time.sleep(0.5)


if __name__ == "__main__":
    pass
