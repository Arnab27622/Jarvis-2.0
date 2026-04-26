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
from assistant.automation.features.music_player import music_player
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
import inspect
from rapidfuzz import process, fuzz

FILLER_WORDS = ["please", "can you", "could you", "would you mind", "hey", "jarvis", "tell me", "i want to", "start", "run"]

def normalize_command(text):
    """
    Normalizes the command text by:
    1. Converting to lowercase
    2. Stripping punctuation
    3. Removing wake word 'jarvis'
    4. Removing common filler words
    5. Trimming whitespace
    """
    if not text:
        return ""
    
    # 1. Lowercase
    text = text.lower().strip()
    
    # 2. Strip punctuation
    text = re.sub(r'[.,?!;:]', '', text)
    
    # 3. Remove wake word 'jarvis'
    text = re.sub(r'\bjarvis\b', '', text).strip()
    
    # 4. Remove filler words from start/end (repeatedly until clean)
    changed = True
    while changed:
        changed = False
        for word in FILLER_WORDS:
            new_text = re.sub(rf'^{word}\b', '', text).strip()
            new_text = re.sub(rf'\b{word}$', '', new_text).strip()
            if new_text != text:
                text = new_text
                changed = True
    
    return text

class CommandRegistry:
    """
    A registry system for managing and executing voice commands.
    Supports tiered matching: Keyword/Exact -> Regex -> Fuzzy.
    """
    def __init__(self):
        self._keyword_handlers = []
        self._regex_handlers = []
        self._fuzzy_handlers = []

    def register_keyword(self, keywords, handler, priority=0):
        if isinstance(keywords, str):
            keywords = [keywords]
        self._keyword_handlers.append((keywords, handler, priority))
        self._keyword_handlers.sort(key=lambda x: x[2], reverse=True)

    def register_regex(self, pattern, handler, priority=0):
        self._regex_handlers.append((re.compile(pattern, re.IGNORECASE), handler, priority))
        self._regex_handlers.sort(key=lambda x: x[2], reverse=True)

    def register_fuzzy(self, phrases, handler, score_cutoff=80, priority=0):
        if isinstance(phrases, str):
            phrases = [phrases]
        self._fuzzy_handlers.append((phrases, handler, score_cutoff, priority))
        self._fuzzy_handlers.sort(key=lambda x: x[3], reverse=True)

    def execute(self, text):
        """
        Find and execute the first matching command handler across tiers.
        """
        # Tier 1: Keyword / Exact Match
        for keywords, handler, _ in self._keyword_handlers:
            if any(kw in text for kw in keywords):
                return self._run_handler(handler, text)

        # Tier 2: Regex Match (for parameters)
        for pattern, handler, _ in self._regex_handlers:
            match = pattern.search(text)
            if match:
                return self._run_handler(handler, text, match)

        # Tier 3: Fuzzy Match (for variations)
        best_overall_match = None
        for phrases, handler, cutoff, _ in self._fuzzy_handlers:
            # Check all phrases for this handler
            match = process.extractOne(text, phrases, scorer=fuzz.WRatio)
            if match and match[1] >= cutoff:
                if best_overall_match is None or match[1] > best_overall_match[1]:
                    best_overall_match = (handler, match[1])
        
        if best_overall_match:
            return self._run_handler(best_overall_match[0], text)

        return False

    def _run_handler(self, handler, text, match=None):
        sig = inspect.signature(handler)
        params = sig.parameters
        
        args = []
        if "text" in params:
            args.append(text)
        elif len(params) > 0 and match:
            # If handler takes arguments and we have a regex match, pass groups
            groups = match.groups()
            if groups:
                args.extend(groups)
            else:
                args.append(match.group(0))
        elif len(params) > 0:
            # Fallback: pass text as first argument
            args.append(text)
            
        handler(*args[:len(params)])
        return True

# Main registry instance
cmd_registry = CommandRegistry()

# Helper decorators
def on_keywords(keywords, priority=0):
    def decorator(handler_func):
        cmd_registry.register_keyword(keywords, handler_func, priority)
        return handler_func
    return decorator

def on_regex(pattern, priority=0):
    def decorator(handler_func):
        cmd_registry.register_regex(pattern, handler_func, priority)
        return handler_func
    return decorator

def on_fuzzy(phrases, score_cutoff=80, priority=0):
    def decorator(handler_func):
        cmd_registry.register_fuzzy(phrases, handler_func, score_cutoff, priority)
        return handler_func
    return decorator

def on_condition(condition_func, priority=0):
    """Legacy/Custom condition support"""
    def decorator(handler_func):
        # We wrap it as a keyword-like check for simplicity in the new loop
        cmd_registry.register_keyword([], lambda text: condition_func(text) and handler_func(text), priority)
        return handler_func
    return decorator



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


# --- Command Handlers ---

@on_condition(lambda text: (text.split()[0] if text else "") in open_input)
def handle_open(text):
    target = " ".join(text.split()[1:])
    open_command(target)

@on_condition(lambda text: (text.split()[0] if text else "") in close_input)
def handle_close():
    close_command()

@on_regex(r"^(?:set\s+)?(?:an\s+)?alarm\s+(?:for|at|in|after)?\s*(.*)$")
@on_fuzzy(["set alarm", "wake me up", "alarm at"])
def handle_set_alarm(text):
    set_alarm(text)

@on_regex(r"^(?:set\s+)?(?:a\s+)?reminder\s+(?:for|at|to|in|after)?\s*(.*)$")
@on_fuzzy(["set reminder", "remind me to", "remember to"])
def handle_set_reminder(text):
    set_reminder(text)

@on_keywords(["list alarms", "show alarms", "what alarms", "my alarms", "check alarms", "list alarm", "show alarm", "what alarm", "my alarm", "check alarm"])
def handle_list_alarms():
    list_alarms()

@on_keywords(["list reminders", "show reminders", "what reminders", "my reminders", "check reminders"])
def handle_list_reminders():
    list_reminders()

@on_keywords(["cancel all alarms", "delete all alarms", "remove all alarms", "clear alarms"])
def handle_cancel_alarms():
    cancel_all_alarms()

@on_keywords(["cancel all reminders", "delete all reminders", "remove all reminders", "clear reminders"])
def handle_cancel_reminders():
    cancel_all_reminders()

@on_keywords(["minimize", "minimise", "minimise the window", "minimize the window"])
def handle_window_minimize():
    handle_minimize()

@on_keywords(["maximize", "maximise", "maximise the window", "maximize the window"])
def handle_window_maximize():
    handle_maximize()

@on_keywords(["restore", "restore window"])
def handle_window_restore():
    handle_restore()

@on_keywords(["switch window", "next window"])
def handle_window_switch_cmd():
    handle_window_switch()

@on_keywords("new tab")
def handle_new_tab():
    ui.hotkey("ctrl", "t")
    speak("New tab opened")

@on_keywords(["incognito", "private tab"])
def handle_incognito():
    open_incognito_tab()

@on_keywords(["bookmark", "bookmark this"])
def handle_bookmark():
    bookmark_page()

@on_keywords(["developer tools", "dev tools"])
def handle_dev_tools():
    open_dev_tools()

@on_keywords(["reload", "refresh"])
def handle_reload():
    reload_page()

@on_keywords(["go back", "back page"])
def handle_back_page():
    go_back()

@on_keywords(["go forward", "forward page"])
def handle_forward_page():
    go_forward()

@on_keywords(["duplicate tab", "duplicate the tab", "duplicate this tab"])
def handle_duplicate():
    duplicate_tab()

@on_keywords("brightness")
def handle_brightness_cmd(text):
    handle_brightness(text)

@on_condition(lambda text: "full screen" in text or "fullscreen" in text)
def handle_fullscreen_logic(text):
    if "video" in text:
        fullscreen_youtube()
    else:
        toggle_fullscreen()

@on_condition(lambda text: any(phrase in text for phrase in ["turn off fullscreen", "turn off full screen"]) and "video" in text)
def handle_video_exit_fullscreen():
    exit_fullscreen_youtube()

@on_keywords(["write", "right"])
def handle_writing(text):
    handle_write(text)

@on_keywords(["enter", "press enter"])
def handle_enter_key():
    ui.press("enter")

@on_keywords(["select all", "select all paragraph"])
def handle_select_all():
    ui.hotkey("ctrl", "a")

@on_keywords(["cut", "cut this"])
def handle_cut():
    ui.hotkey("ctrl", "x")

@on_keywords(["copy", "copy this"])
def handle_copy_cmd():
    ui.hotkey("ctrl", "c")

@on_keywords(["paste", "paste here"])
def handle_paste_cmd():
    ui.hotkey("ctrl", "v")

@on_keywords(["undo", "undo it"])
def handle_undo_cmd():
    ui.hotkey("ctrl", "z")

@on_keywords(["redo", "redo it"])
def handle_redo_cmd():
    ui.hotkey("ctrl", "y")

@on_keywords("copy last paragraph")
def handle_copy_last():
    ui.hotkey("ctrl", "shift", "c")

@on_keywords(["screenshot", "take screenshot"])
def handle_screenshot_cmd():
    take_screenshot()

@on_keywords(["check internet speed", "check the internet speed", "run internet speed test", "check internet connection"])
def handle_speedtest():
    check_internet_speed()

@on_keywords(["run speaker health test", "check the speaker health", "check speaker health", "check the speaker"])
def handle_speaker_health():
    speaker_health_test()

@on_keywords(["run mic health test", "check the mic health", "check mic health", "check the mic", "run mike health test", "check the mike health", "check mike health", "check the mike"])
def handle_mic_health_cmd():
    mic_health()

@on_keywords(["scroll up", "scroll down"])
def handle_scrolling(text):
    handle_scroll(text)

@on_keywords(["scroll to top", "scroll to the top"])
def handle_scroll_top():
    handle_scroll_to_top()

@on_keywords(["scroll to bottom", "scroll to the bottom"])
def handle_scroll_bottom():
    handle_scroll_to_bottom()

@on_keywords("page up")
def handle_page_up():
    speak("Scrolling page up")
    ui.press("pageup")

@on_keywords("page down")
def handle_page_down():
    speak("Scrolling page down")
    ui.press("pagedown")

@on_keywords(["play music", "play some music", "start music", "play random music"])
def handle_play_music():
    music_player.play_random_music()

@on_keywords(["play song", "play the song"])
def handle_play_song(text):
    if "play song" in text:
        song_name = text.split("play song")[1].strip()
    elif "play the song" in text:
        song_name = text.split("play the song")[1].strip()
    else:
        song_name = text.replace("play", "").strip()
    if song_name:
        music_player.play_specific_song(song_name)
    else:
        speak("Which song would you like me to play?")

@on_keywords(["pause music", "pause the music", "pause song", "pause the song"])
def handle_pause_music():
    music_player.pause_music()
@on_keywords(["resume music", "resume the music", "continue music", "unpause music"])
def handle_resume_music():
    music_player.resume_music()

@on_keywords(["stop music", "stop the music", "stop song", "stop the song"])
def handle_stop_music():
    music_player.stop_music()

@on_keywords(["next track", "next song", "play next", "play next song", "play the next song"])
def handle_next_track():
    music_player.next_track()

@on_keywords(["previous track", "previous song", "play previous", "play previous song", "play the previous song", "last song"])
def handle_prev_track():
    music_player.previous_track()

@on_keywords(["increase music volume", "music volume up", "louder music"])
def handle_inc_music_vol():
    music_player.increase_volume()

@on_keywords(["decrease music volume", "music volume down", "softer music"])
def handle_dec_music_vol():
    music_player.decrease_volume()

@on_keywords(["what's playing", "current track", "which song is this", "what song is playing"])
def handle_current_track_query():
    cur = music_player.get_current_track()
    if cur:
        speak(f"Currently playing: {cur}")
    else:
        speak("No music is currently playing")

@on_keywords(["current location", "where am i"])
def handle_location():
    get_current_location()

@on_regex(r"^play\s+(.*?)\s*(?:on\s+youtube|youtube)?$")
def handle_youtube_play(q):
    play_on_youtube(q)

@on_regex(r"^search\s+for\s+(.*?)\s*(?:on\s+youtube|youtube)?$")
def handle_youtube_search(q):
    search_on_youtube(q)

@on_keywords("previous video")
def handle_yt_prev():
    previous_video()

@on_keywords("next video")
def handle_yt_next():
    next_video()

@on_keywords(["pause video", "pause the video"])
def handle_yt_pause():
    pause_youtube()

@on_keywords(["replay video", "replay the video"])
def handle_yt_replay():
    replay_video()

@on_condition(lambda text: any(phrase in text for phrase in ["resume", "play"]) and "video" in text)
def handle_yt_resume():
    resume_youtube()

@on_keywords(["unmute video", "unmute the video"])
def handle_yt_unmute():
    unmute_youtube()

@on_keywords(["mute video", "mute the video"])
def handle_yt_mute():
    mute_youtube()

@on_keywords(["turn on subtitles", "subtitles on"])
def handle_yt_subs_on():
    turn_on_subtitles()

@on_keywords(["turn off subtitles", "subtitles off"])
def handle_yt_subs_off():
    turn_off_subtitles()

@on_condition(lambda text: any(phrase in text for phrase in ["volume up", "increase volume", "increase the volume"]) and "video" in text)
def handle_yt_vol_up():
    control_youtube_video("volume increase")

@on_condition(lambda text: any(phrase in text for phrase in ["volume down", "decrease volume", "decrease the volume"]) and "video" in text)
def handle_yt_vol_down():
    control_youtube_video("volume decrease")

@on_keywords("skip backward")
def handle_yt_skip_back():
    skip_backward_video()

@on_keywords("skip video")
def handle_yt_skip_fwd():
    skip_video()

@on_fuzzy(["increase volume", "volume up", "make it louder", "louder", "up the volume"])
def handle_system_vol_up():
    handle_volume_change("increase")

@on_fuzzy(["decrease volume", "volume down", "make it softer", "softer", "lower volume", "down the volume"])
def handle_system_vol_down():
    handle_volume_change("decrease")

@on_keywords("unmute")
def handle_sys_unmute():
    ui.hotkey("volumemute")
    speak("Volume unmuted")

@on_keywords("mute")
def handle_sys_mute():
    speak("Muting volume")
    ui.press("volumemute")

@on_regex(r"^search\s+the\s+web\s+for\s+(.*)$")
@on_regex(r"^search\s+web\s+for\s+(.*)$")
def handle_web_search_action(search_text):
    speak(f"Searching the web for {search_text}. Please wait a moment...")
    generate(user_prompt=search_text, prints=True)

@on_regex(r"^search\s+for\s+(.*?)\s*(?:on\s+google|google)?$")
def handle_google_search(search_text):
    handle_web_search(search_text)

@on_condition(lambda text: "search for" in text and any(phrase in text for phrase in ["in wikipedia", "from wikipedia", "on wikipedia"]))
def handle_wiki_search_action(text):
    patterns = ["search for", "in wikipedia", "from wikipedia", "on wikipedia"]
    search_text = text
    for pattern in patterns:
        if pattern in text:
            search_text = text.replace(pattern, "").strip()
    speak("Searching the wikipedia...")
    wiki_search(search_text)

@on_keywords(["what time", "what's the time", "what's the current time"])
def handle_time_query():
    tell_time()

@on_keywords(["what date", "what's the date"])
def handle_date_query():
    tell_date()

@on_keywords(["tell a joke", "tell me a joke", "a joke"])
def handle_joke_cmd():
    tell_joke()

@on_keywords(["system info", "system status"])
def handle_sys_info():
    get_system_info()

@on_keywords(["battery percentage", "battery status"])
def handle_battery_stat():
    battery_monitor.battery_percentage()

@on_keywords(["check ip address", "check my ip address"])
def handle_ip_check():
    check_ip_address()

@on_keywords(["check running apps", "check the running apps"])
def handle_running_apps():
    check_running_app()

@on_keywords(["create an image of", "create image of", "generate an image of", "generate image of"])
def handle_image_gen(text):
    patterns = ["create an image of", "create image of", "generate an image of", "generate image of"]
    prompt = text
    for pattern in patterns:
        if pattern in text:
            prompt = text.replace(pattern, "").strip()
            break
    speak(f"Generating image of {prompt}. Please wait a moment...")
    generate_image_from_text(prompt)

@on_keywords(["check temperature", "check the temperature"])
def handle_temp():
    speak("Checking the temperature. Please wait a moment...")
    get_current_temperature()

@on_keywords(["what's the weather today", "check today's weather"])
def handle_weather_today():
    speak("Checking Today's weather conditions. Please wait a moment...")
    get_overall_weather()

@on_keywords(["check the weather of", "check weather of"])
def handle_weather_location(text):
    weather_patterns = ["check the weather of", "check weather of"]
    address = text
    for pattern in weather_patterns:
        if pattern in text:
            address = text.replace(pattern, "").strip()
            break
    speak(f"Checking the weather in {address}. Please wait a moment...")
    get_weather_by_address(address=address)

@on_keywords(["tell me news", "what's the news", "today's news", "latest news", "news headlines", "top headlines", "current news"])
def handle_news_cmd():
    tell_news()

@on_keywords("remember that")
def handle_remember(text):
    remember_info(text)

@on_keywords("what did i ask you to remember")
def handle_recall():
    recall_info()

@on_keywords("shutdown")
def handle_shutdown_cmd():
    speak("Shutting down the system in 10 seconds")
    os.system("shutdown /s /t 10")

@on_keywords("restart")
def handle_restart_cmd():
    speak("Restarting the system in 10 seconds")
    os.system("shutdown /r /t 10")


def process_command(text):
    """
    Process and execute voice commands using a modular registry system.
    """
    # Normalize the text (removes jarvis, filler words, etc.)
    normalized_text = normalize_command(text)
    
    if not normalized_text:
        welcome()
        return

    # Attempt to execute command from registry
    if not cmd_registry.execute(normalized_text):
        # Fallback to AI brain for unrecognized commands
        brain(normalized_text)


if __name__ == "__main__":
    pass
