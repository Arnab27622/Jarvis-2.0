"""
Main command module for the Voice Assistant.

This module handles the core command processing logic, including wake word detection,
command mode management, and routing of various voice commands to their respective
functionalities. It serves as the central coordinator for all assistant capabilities.
"""

from assistant.interface.welcome import welcome
from assistant.activities.advice import rand_advice
from assistant.activities.activity_monitor import *
from assistant.activities.check_speaker_health import speaker_health_test
from assistant.activities.check_mic_health import mic_health
from assistant.activities.battery_features import battery_monitor
from assistant.automation.features.window_automation import *
from assistant.automation.features.utility_automation import *
from assistant.automation.text_to_image.text_to_image import generate_image_from_text
from assistant.automation.integrations.detailed_web_search import generate
from assistant.automation.integrations.wiki_search import wiki_search
from assistant.automation.integrations.news_automation import tell_news
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
from assistant.automation.app_control.open import open_command
from assistant.automation.app_control.close import close_command
from assistant.core.ear import listen
from assistant.core.brain import brain
from data.dlg_data.dlg import *
import random
import re
import pyautogui as ui
import os


def wait_for_wakeword():
    """
    Wait for the hotword/wake word to be spoken.

    This function continuously listens for audio input and checks for:
    - Wake words to activate command mode
    - Exit commands to terminate the assistant
    - Confirmation responses for pending advice prompts

    Returns:
        bool: True when wake word detected (entering command mode),
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

    This function implements a state machine with two main states:
    1. Waiting for wake word (command_mode = False)
    2. Active command processing (command_mode = True)

    The loop handles:
    - Wake word detection to enter command mode
    - Command processing in active mode
    - Sleep commands to return to wake word waiting
    - Exit commands to terminate the assistant
    - Activity monitoring and confirmation handling
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
    """
    Process and execute voice commands.

    This function serves as the main command router, parsing voice input
    and delegating to appropriate functionality modules. It handles:
    - Command normalization (removing wake word)
    - Application control (open/close)
    - Alarm and reminder management
    - Window and browser control
    - System utilities
    - Media and entertainment
    - Information retrieval
    - And many other features

    Args:
        text (str): The voice command text to process
    """
    # Remove wake word from command if present
    if "jarvis" in text:
        text = re.sub(r"\bjarvis\b", "", text).strip()
        if not text:
            welcome()
            return

    first_word = text.split()[0] if text else ""

    # Application Control
    if first_word in open_input:
        target = " ".join(text.split()[1:])
        open_command(target)
    elif first_word in close_input:
        close_command()

    # Alarm and Reminder Management
    elif any(
        phrase in text
        for phrase in [
            "set alarm",
            "set an alarm",
            "alarm for",
            "alarm at",
            "wake me",
            "wake up",
            "alarm in",
            "alarm after",
        ]
    ):
        set_alarm(text)
    elif any(
        phrase in text
        for phrase in [
            "set reminder",
            "remind me",
            "reminder for",
            "reminder at",
            "remember to",
            "don't forget",
            "remind me in",
            "remind me after",
            "reminder in",
            "reminder after",
        ]
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
            "list alarm",
            "show alarm",
            "what alarm",
            "my alarm",
            "check alarm",
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

    # Window Management
    elif any(
        phrase in text
        for phrase in [
            "minimize",
            "minimise",
            "minimise the window",
            "minimize the window",
        ]
    ):
        handle_minimize()
    elif any(
        phrase in text
        for phrase in [
            "maximize",
            "maximise",
            "maximise the window",
            "maximize the window",
        ]
    ):
        handle_maximize()
    elif "restore" in text or "restore window" in text:
        handle_restore()
    elif "switch window" in text or "next window" in text:
        handle_window_switch()

    # Browser Control
    elif "new tab" in text:
        ui.hotkey("ctrl", "t")
        speak("New tab opened")
    elif "incognito" in text or "private tab" in text:
        open_incognito_tab()
    elif "bookmark" in text or "bookmark this" in text:
        bookmark_page()
    elif "developer tools" in text or "dev tools" in text:
        open_dev_tools()
    elif "reload" in text or "refresh" in text:
        reload_page()
    elif "go back" in text or "back page" in text:
        go_back()
    elif "go forward" in text or "forward page" in text:
        go_forward()
    elif any(
        phrase in text
        for phrase in ["duplicate tab", "duplicate the tab", "duplicate this tab"]
    ):
        duplicate_tab()

    # Screen and Display Control
    elif "brightness" in text:
        handle_brightness(text)
    elif "full screen" in text or "fullscreen" in text:
        if "video" in text:  # For youtube video
            fullscreen_youtube()
        else:  # For general purpose
            toggle_fullscreen()
    elif (
        any(
            phrase in text for phrase in ["turn off fullscreen", "turn off full screen"]
        )
        and "video" in text
    ):
        exit_fullscreen_youtube()

    # Text Input and Editing
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

    # System Utilities
    elif "screenshot" in text or "take screenshot" in text:
        take_screenshot()
    elif any(
        phrase in text
        for phrase in [
            "check internet speed",
            "check the internet speed",
            "run internet speed test",
            "check internet connection",
        ]
    ):
        check_internet_speed()
    elif any(
        phrase in text
        for phrase in [
            "run speaker health test",
            "check the speaker health",
            "check speaker health",
            "check the speaker",
        ]
    ):
        speaker_health_test()
    elif any(
        phrase in text
        for phrase in [
            "run mic health test",
            "check the mic health",
            "check mic health",
            "check the mic",
            "run mike health test",
            "check the mike health",
            "check mike health",
            "check the mike",
        ]
    ):
        mic_health()

    # Scroll Control
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

    # Location Services
    elif "current location" in text or "where am i" in text:
        get_current_location()

    # YouTube Control
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
    elif any(phrase in text for phrase in ["resume", "play"]) and "video" in text:
        resume_youtube()
    elif "unmute" in text and "video" in text:
        unmute_youtube()
    elif "mute" in text and "video" in text:
        mute_youtube()
    elif "turn on" in text and "subtitles" in text and "video" in text:
        turn_on_subtitles()
    elif "turn off" in text and "subtitles" in text and "video" in text:
        turn_off_subtitles()
    elif (
        any(
            phrase in text
            for phrase in ["volume up", "increase volume", "increase the volume"]
        )
        and "video" in text
    ):
        control_youtube_video("volume increase")
    elif (
        any(
            phrase in text
            for phrase in ["volume down", "decrease volume", "decrease the volume"]
        )
        and "video" in text
    ):
        control_youtube_video("volume decrease")
    elif "skip backward" in text and "video" in text:
        skip_backward_video()
    elif "skip" in text and "video" in text:
        skip_video()

    # Audio Control
    elif any(phrase in text for phrase in ["increase volume", "increase the volume"]):
        handle_volume_change("increase")
    elif any(phrase in text for phrase in ["decrease volume", "decrease the volume"]):
        handle_volume_change("decrease")
    elif "unmute" in text:
        ui.hotkey("volumemute")
        speak("Volume unmuted")
    elif "mute" in text:
        speak("Muting volume")
        ui.press("volumemute")

    # Search Functions
    elif "search the web for" in text or "search web for" in text:
        patterns = ["search the web for", "search web for"]
        for pattern in patterns:
            if pattern in text:
                search_text = text.replace(pattern, "").strip()
        speak(f"Searching the web for {search_text}. Please wait a moment...")
        generate(user_prompt=text, prints=True)
    elif "search for" in text and "google" in text:
        handle_web_search(text)
    elif "search for" in text and any(
        phrase in text for phrase in ["in wikipedia", "from wikipedia", "on wikipedia"]
    ):
        patterns = ["search for", "in wikipedia", "from wikipedia", "on wikipedia"]
        for pattern in patterns:
            if pattern in text:
                search_text = text.replace(pattern, "").strip()
        speak("Searching the wikipedia...")
        wiki_search(search_text)

    # Time and Date
    elif any(
        phrase in text
        for phrase in ["what time", "what's the time", "what's the current time"]
    ):
        tell_time()
    elif "what date" in text or "what's the date" in text:
        tell_date()

    # Entertainment
    elif any(phrase in text for phrase in ["tell a joke", "tell me a joke", "a joke"]):
        tell_joke()

    # System Information
    elif "system info" in text or "system status" in text:
        get_system_info()
    elif "battery percentage" in text or "battery status" in text:
        battery_monitor.battery_percentage()
    elif "check ip address" in text or "check my ip address" in text:
        check_ip_address()
    elif "check running apps" in text or "check the running apps" in text:
        check_running_app()

    # Image Generation
    elif any(
        phrase in text
        for phrase in [
            "create an image of",
            "create image of",
            "generate an image of",
            "generate image of",
        ]
    ):
        patterns = [
            "create an image of",
            "create image of",
            "generate an image of",
            "generate image of",
        ]
        for pattern in patterns:
            if pattern in text:
                prompt = text.replace(pattern, "").strip()
        speak(f"Generating image of {prompt}. Please wait a moment...")
        generate_image_from_text(prompt)

    # Weather Information
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

    # News Information
    elif any(
        phrase in text
        for phrase in [
            "tell me news",
            "what's the news",
            "today's news",
            "latest news",
            "news headlines",
            "top headlines",
            "current news",
        ]
    ):
        tell_news()

    # Memory Functions
    elif "remember that" in text:
        remember_info(text)
    elif "what did i ask you to remember" in text:
        recall_info()

    # System Control
    elif "shutdown" in text:
        speak("Shutting down the system in 10 seconds")
        os.system("shutdown /s /t 10")
    elif "restart" in text:
        speak("Restarting the system in 10 seconds")
        os.system("shutdown /r /t 10")

    # Fallback to AI brain for unrecognized commands
    else:
        brain(text)


if __name__ == "__main__":
    pass
