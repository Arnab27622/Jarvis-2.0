from assistant.interface.welcome import welcome
from assistant.activities.advice import rand_advice
from assistant.activities.activity_monitor import *
from assistant.activities.check_speaker_health import speaker_health_test
from assistant.activities.check_mic_health import mic_health
from assistant.automation.features.window_automation import *
from assistant.automation.features.utility_automation import *
from assistant.automation.integrations.location_automation import (
    get_current_location,
    check_ip_address,
)
from assistant.automation.integrations.alarm_reminder import (
    set_alarm,
    set_reminder,
    list_alarms,
    list_reminders,
    cancel_all_alarms,
    cancel_all_reminders,
)
from assistant.automation.integrations.check_weather import (
    get_current_temperature,
    get_overall_weather,
    get_weather_by_address,
)
from assistant.automation.integrations.google_search_automation import handle_web_search
from assistant.automation.integrations.task_schedule_automation import (
    recall_info,
    remember_info,
)
from assistant.automation.integrations.jokes_automation import tell_joke
from assistant.automation.integrations.datetime_automation import tell_date, tell_time
from assistant.automation.integrations.internet_speed import check_internet_speed
from assistant.automation.integrations.youtube_automation import *
from assistant.core.ear import listen
from assistant.core.brain import brain
from assistant.automation.app_control.open import open_command
from assistant.automation.app_control.close import close_command
from assistant.activities.battery_features import battery_monitor
from data.dlg_data.dlg import *
import random
import re
import pyautogui as ui
import os


def wait_for_wakeword():
    """
    Wait for the hotword/wake word to be spoken.
    Returns:
        True when wake word detected (entering command mode)
        False if a close command is detected to exit loop
    """
    speak("Awaiting your command...")

    while True:
        text = listen()
        if text is None:
            continue

        text_lower = text.lower().strip()

        # Check for confirmation prompt response as well
        if activity_monitor.awaiting_confirmation:
            result = activity_monitor.handle_confirmation_response(text)
            if result is True:
                advice = rand_advice()
                if advice:
                    speak(advice)
                continue
            elif result is False:
                # User declined advice, continue listening for wake word
                continue
            # If result is None, check for timeout
            elif activity_monitor.check_confirmation_timeout():
                # Timeout occurred, reset and continue listening for wake word
                activity_monitor.reset_confirmation_state()
                continue

        if any(keyword.strip() == text_lower for keyword in wakeup_key_word):
            # Reset any pending advice confirmation when waking up
            activity_monitor.reset_confirmation_state()
            welcome()
            return True

        if any(keyword in text_lower for keyword in bye_key_word):
            response = random.choice(res_bye)
            speak(response)
            stop_activity_monitoring()
            return False


def command():
    """
    Main command loop managing wake word state and command mode.
    Listens for wake word to enter command mode.
    In command mode, processes commands continuously.
    'sleep' command returns to waiting for wake word.
    """
    start_activity_monitoring()

    # State: False = waiting for wake word, True = in command mode
    command_mode = False

    while True:
        text = listen()
        if text is None:
            print("Sorry, I couldn't understand. Please try again.")
            continue

        text_lower = text.lower().strip()

        # Always check confirmation responses first
        if activity_monitor.awaiting_confirmation:
            result = activity_monitor.handle_confirmation_response(text)
            if result is True:
                advice = rand_advice()
                if advice:
                    speak(advice)
                continue
            elif result is False:
                # User declined advice, continue with normal flow
                continue
            # If result is None, check for timeout
            elif activity_monitor.check_confirmation_timeout():
                # Timeout occurred, reset and continue with normal flow
                activity_monitor.reset_confirmation_state()
                # Don't continue here, let the command processing happen

        # Exit commands handled anytime
        if any(keyword in text_lower for keyword in bye_key_word):
            response = random.choice(res_bye)
            speak(response)
            stop_activity_monitoring()
            break

        # If not in command mode, wait for wake word
        if not command_mode:
            if any(keyword.strip() == text_lower for keyword in wakeup_key_word):
                # Reset any pending advice confirmation when waking up
                activity_monitor.reset_confirmation_state()
                welcome()
                command_mode = True
            # Ignore other inputs outside command mode
            continue

        # In command mode, check if user wants to sleep and exit command mode
        if any(keyword.strip() == text_lower for keyword in stopcmd):
            speak(random.choice(stopdlg))
            command_mode = False
            continue

        # Record activity for normal commands
        record_user_activity()

        # Process commands normally in command mode
        process_command(text_lower)


def process_command(text):
    """Process command whether they contain 'jarvis' or not"""
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

    elif any(
        phrase in text
        for phrase in ["set alarm", "set an alarm", "alarm for", "alarm at"]
    ):
        set_alarm(text)

    elif any(
        phrase in text
        for phrase in ["set reminder", "remind me", "reminder for", "reminder at"]
    ):
        set_reminder(text)

    elif any(
        phrase in text
        for phrase in [
            "list alarms",
            "show alarms",
            "what alarms",
            "my alarms",
            "check alarms",
        ]
    ):
        list_alarms()

    elif any(
        phrase in text
        for phrase in [
            "list reminders",
            "show reminders",
            "what reminders",
            "my reminders",
            "check reminders",
        ]
    ):
        list_reminders()

    elif any(
        phrase in text
        for phrase in [
            "cancel all alarms",
            "delete all alarms",
            "remove all alarms",
            "clear alarms",
        ]
    ):
        cancel_all_alarms()

    elif any(
        phrase in text
        for phrase in [
            "cancel all reminders",
            "delete all reminders",
            "remove all reminders",
            "clear reminders",
        ]
    ):
        cancel_all_reminders()

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

    elif (
        "fullscreen" in text or "full screen" in text
    ) and "video" in text:  # For youtube video
        fullscreen_youtube()

    elif (
        "turn off" in text
        and ("fullscreen" in text or "full screen" in text)
        and "video" in text
    ):  # For youtube video
        exit_fullscreen_youtube()

    elif "full screen" in text or "fullscreen" in text:  # For general purpose
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

    elif "screenshot" in text or "take screenshot" in text:
        take_screenshot()

    elif (
        "check internet speed" in text
        or "check the internet speed" in text
        or "run internet speed test" in text
        or "check internet connection" in text
    ):
        check_internet_speed()

    elif (
        "run speaker health test" in text
        or "check the speaker health" in text
        or "check speaker health" in text
        or "check the speaker" in text
    ):
        speaker_health_test()

    elif (
        "run mic health test" in text
        or "check the mic health" in text
        or "check mic health" in text
        or "check the mic" in text
        or "run mike health test" in text
        or "check the mike health" in text
        or "check mike health" in text
        or "check the mike" in text
    ):
        mic_health()

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

    elif "previous video" in text:
        previous_video()

    elif "next video" in text:
        next_video()

    elif "pause" in text and "video" in text:
        pause_youtube()

    elif "replay" in text and "video" in text:
        replay_video()

    elif ("resume" in text or "play" in text) and "video" in text:
        resume_youtube()

    elif "unmute" in text and "video" in text:  # For youtube video
        unmute_youtube()

    elif "mute" in text and "video" in text:  # For youtube video
        mute_youtube()

    elif "turn on" in text and "subtitles" in text and "video" in text:
        turn_on_subtitles()

    elif "turn off" in text and "subtitles" in text and "video" in text:
        turn_off_subtitles()

    elif (
        "volume up" in text
        or "increase volume" in text
        or "increase the volume" in text
    ) and "video" in text:  # For youtube video
        control_youtube_video("volume increase")

    elif (
        "volume down" in text
        or "decrease volume" in text
        or "decrease the volume" in text
    ) and "video" in text:  # For youtube video
        control_youtube_video("volume decrease")

    elif "skip backward" in text and "video" in text:
        skip_backward_video()

    elif "skip" in text and "video" in text:
        skip_video()

    elif (
        "increase volume" in text or "increase the volume" in text
    ):  # For general purpose
        handle_volume_change("increase")

    elif (
        "decrease volume" in text or "decrease the volume" in text
    ):  # For general purpose
        handle_volume_change("decrease")

    elif "unmute" in text:  # For general purpose
        ui.hotkey("volumemute")
        speak("Volume unmuted")

    elif "mute" in text:  # For general purpose
        speak("Muting volume")
        ui.press("volumemute")

    elif "search for" in text and "google" in text:
        handle_web_search(text)

    elif (
        "what time" in text
        or "what's the time" in text
        or "what's the current time" in text
    ):
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

    elif "check running apps" in text or "check the running apps" in text:
        check_running_app()

    elif "check temperature" in text or "check the temperature" in text:
        speak("Checking the temperature. Please wait a moment...")
        get_current_temperature()

    elif "what's the weather today" in text or "check today's weather" in text:
        speak("Checking Today's weather conditions. Please wait a moment...")
        get_overall_weather()

    elif "check the weather of" in text or "check weather of" in text:
        weather_patterns = ["check the weather of", "check weather of"]
        for pattern in weather_patterns:
            if pattern in text:
                address = text.replace(pattern, "").strip()

        speak(f"Checking the weather in {address}. Please wait a moment...")
        get_weather_by_address(address=address)

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

    else:
        brain(text)


if __name__ == "__main__":
    pass
