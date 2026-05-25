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
import time
from rapidfuzz import process, fuzz

FILLER_WORDS = ["please", "can you", "could you", "would you mind", "hey", "jarvis", "tell me", "i want to", "start", "run"]
DEBUG_REGISTRY = True

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
    
    # 2. Strip only "ending" punctuation that doesn't affect internal logic
    # We keep . and : for times/dates, and ' for contractions
    text = re.sub(r'[?,!;]', '', text)
    
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
                if DEBUG_REGISTRY:
                    print(f"[Registry] Exact Match: '{text}' -> {handler.__name__}")
                return self._run_handler(handler, text)

        # Tier 2: Regex Match (for parameters)
        for pattern, handler, _ in self._regex_handlers:
            match = pattern.search(text)
            if match:
                if DEBUG_REGISTRY:
                    print(f"[Registry] Regex Match: '{pattern.pattern}' -> {handler.__name__}")
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
            if DEBUG_REGISTRY:
                print(f"[Registry] Fuzzy Match: '{text}' (Score: {best_overall_match[1]:.1f}) -> {best_overall_match[0].__name__}")
            return self._run_handler(best_overall_match[0], text)

        return False

    def _run_handler(self, handler, text, match=None):
        sig = inspect.signature(handler)
        params = sig.parameters
        
        # 1. Try named capture groups from regex (highest precision)
        if match and hasattr(match, 'groupdict'):
            kwargs = match.groupdict()
            valid_kwargs = {k: v for k, v in kwargs.items() if k in params}
            if valid_kwargs:
                handler(**valid_kwargs)
                return True
                
        # 2. Fallback: Positional logic
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
            # Final fallback: pass text as first argument
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

        # Record activity for normal commands
        record_user_activity()

        # Normalize text for checking sleep commands and general processing
        normalized_text = normalize_command(text_lower)

        # In command mode, check if user wants to sleep and exit command mode
        if any(keyword.strip() == normalized_text for keyword in stopcmd):
            speak(random.choice(stopdlg))
            command_mode = False
            continue

        # Process commands normally in command mode
        try:
            process_command(normalized_text)
        except Exception as e:
            print(f"Error in command execution: {e}")
            speak("I encountered an internal problem while executing that command.")


# --- Command Handlers ---

@on_regex(r"\b(?:open|launch|start)\s+(?P<target>.*)$")
def handle_open(target):
    open_command(target)

@on_regex(r"\b(?:close|exit|terminate|kill)\s+(?P<app_name>.+)$")
@on_fuzzy(["close", "exit", "close that", "close app"], score_cutoff=90)
def handle_close(app_name=None):
    close_command(app_name)

@on_regex(r"(?:set\s+)?(?:an\s+)?alarm\s+(?:for|at|in|after)?\s*(?P<time_text>.*)$")
@on_fuzzy(["set alarm", "wake me up", "alarm at"], score_cutoff=90)
def handle_set_alarm(text):
    set_alarm(text)

@on_regex(r"\b(?:remind\s+me\s+(?:to|about|that)|remember\s+to)\s+(?P<reminder_text>.*)$")
@on_regex(r"\b(?:set\s+)?(?:a\s+)?reminder\s+(?:for|at|in|after)?\s*(?P<reminder_text>.*)$")
@on_fuzzy(["set reminder", "remind me to", "remember to"], score_cutoff=90)
def handle_set_reminder(text):
    set_reminder(text)

@on_fuzzy(["list alarms", "show alarms", "what alarms", "my alarms", "check alarms"], score_cutoff=90)
def handle_list_alarms():
    list_alarms()

@on_fuzzy(["list reminders", "show reminders", "what reminders", "my reminders", "check reminders"], score_cutoff=90)
def handle_list_reminders():
    list_reminders()

@on_fuzzy(["cancel all alarms", "cancel alarm", "delete alarms", "remove alarms", "clear alarms"], score_cutoff=90)
def handle_cancel_alarms():
    cancel_all_alarms()

@on_fuzzy(["cancel all reminders", "cancel reminder", "delete reminders", "remove reminders", "clear reminders"], score_cutoff=90)
def handle_cancel_reminders():
    cancel_all_reminders()

@on_fuzzy(["minimize", "minimise", "minimise the window", "minimize the window", "minimize window"], score_cutoff=90)
def handle_window_minimize():
    handle_minimize()

@on_fuzzy(["maximize", "maximise", "maximise the window", "maximize the window", "maximize window"], score_cutoff=90)
def handle_window_maximize():
    handle_maximize()

@on_fuzzy(["restore", "restore window", "restore the window"], score_cutoff=90)
def handle_window_restore():
    handle_restore()

@on_fuzzy(["switch window", "next window", "change window"], score_cutoff=90)
def handle_window_switch_cmd():
    handle_window_switch()

@on_fuzzy(["new tab", "open new tab", "open a new tab"], score_cutoff=90)
def handle_new_tab():
    ui.hotkey("ctrl", "t")
    speak("New tab opened")

@on_fuzzy(["incognito", "private tab", "secret mode", "incognito mode"], score_cutoff=90)
def handle_incognito():
    open_incognito_tab()

@on_fuzzy(["bookmark", "bookmark this", "bookmark this page", "save this page"], score_cutoff=90)
def handle_bookmark():
    bookmark_page()

@on_fuzzy(["developer tools", "dev tools", "open dev tools"], score_cutoff=90)
def handle_dev_tools():
    open_dev_tools()

@on_fuzzy(["reload", "refresh", "reload page", "refresh page"], score_cutoff=90)
def handle_reload():
    reload_page()

@on_fuzzy(["go back", "back page", "previous page"], score_cutoff=90)
def handle_back_page():
    go_back()

@on_fuzzy(["go forward", "forward page", "next page"], score_cutoff=90)
def handle_forward_page():
    go_forward()

@on_fuzzy(["duplicate tab", "duplicate the tab", "duplicate this tab"], score_cutoff=90)
def handle_duplicate():
    duplicate_tab()

@on_regex(r"(?P<text>.*brightness.*)$")
def handle_brightness_cmd(text):
    handle_brightness(text)

@on_regex(r"(?P<text>.*(?:full\s*screen|fullscreen).*)$")
def handle_fullscreen_logic(text):
    if "video" in text:
        fullscreen_youtube()
    else:
        toggle_fullscreen()

@on_regex(r"turn\s+off\s+full\s*screen.*video")
def handle_video_exit_fullscreen():
    exit_fullscreen_youtube()

@on_regex(r"\b(?:please\s+)?\b(?:write|right|type)\s+(?P<content>.*)$")
def handle_writing(content):
    handle_write(content)

@on_fuzzy(["enter", "press enter", "hit enter"], score_cutoff=90)
def handle_enter_key():
    ui.press("enter")

@on_fuzzy(["select all", "select all paragraph", "select everything"], score_cutoff=90)
def handle_select_all():
    ui.hotkey("ctrl", "a")

@on_fuzzy(["cut", "cut this", "cut text"], score_cutoff=90)
def handle_cut():
    ui.hotkey("ctrl", "x")

@on_fuzzy(["copy", "copy this", "copy text"], score_cutoff=90)
def handle_copy_cmd():
    ui.hotkey("ctrl", "c")

@on_fuzzy(["paste", "paste here", "paste this"], score_cutoff=90)
def handle_paste_cmd():
    ui.hotkey("ctrl", "v")

@on_fuzzy(["undo", "undo it", "undo that"], score_cutoff=90)
def handle_undo_cmd():
    ui.hotkey("ctrl", "z")

@on_fuzzy(["redo", "redo it", "redo that"], score_cutoff=90)
def handle_redo_cmd():
    ui.hotkey("ctrl", "y")

@on_fuzzy(["copy last paragraph", "copy the last paragraph"], score_cutoff=90)
def handle_copy_last():
    ui.hotkey("ctrl", "shift", "c")

@on_fuzzy(["screenshot", "take screenshot", "take a screenshot"], score_cutoff=90)
def handle_screenshot_cmd():
    take_screenshot()

@on_fuzzy(["check internet speed", "check the internet speed", "run internet speed test", "check internet connection", "internet speed"], score_cutoff=90)
def handle_speedtest():
    check_internet_speed()

@on_fuzzy(["run speaker health test", "check the speaker health", "check speaker health", "check the speaker", "speaker health"], score_cutoff=90)
def handle_speaker_health():
    speaker_health_test()

@on_fuzzy(["run mic health test", "check the mic health", "check mic health", "check the mic", "mic health", "mike health"], score_cutoff=90)
def handle_mic_health_cmd():
    mic_health()

@on_regex(r"(?:scroll|page)\s*(?:to\s+(?:the\s+)?)?\s*(?P<direction>up|down|top|bottom)")
@on_fuzzy(["scroll up", "scroll down", "scroll to top", "scroll to bottom",
           "page up", "page down"], score_cutoff=90)
def handle_scroll_cmd(text=None, direction=None):
    d = (direction or text or "").lower()
    if "top" in d:
        handle_scroll_to_top()
    elif "bottom" in d:
        handle_scroll_to_bottom()
    elif "page" in d and "up" in d:
        speak("Scrolling page up")
        ui.press("pageup")
    elif "page" in d and "down" in d:
        speak("Scrolling page down")
        ui.press("pagedown")
    else:
        handle_scroll(text or d)

@on_regex(r"\b(?P<action>play|pause|resume|stop|next|previous|last)\b\s*(?:the\s+)?(?:music|song|track)")
@on_fuzzy(["play music", "play some music", "start music", "play random music",
           "pause music", "pause the music", "pause song",
           "resume music", "resume the music", "continue music", "unpause music",
           "stop music", "stop the music", "stop song",
           "next track", "next song", "play next",
           "previous track", "previous song", "play previous", "last song",
           "increase music volume", "music volume up", "louder music",
           "decrease music volume", "music volume down", "softer music"], score_cutoff=90)
def handle_music_control(text=None, action=None):
    cmd = (action or text or "").lower()
    if "pause" in cmd:
        music_player.pause_music()
    elif any(w in cmd for w in ["resume", "continue", "unpause"]):
        music_player.resume_music()
    elif "stop" in cmd:
        music_player.stop_music()
    elif "next" in cmd:
        music_player.next_track()
    elif any(w in cmd for w in ["previous", "last"]):
        music_player.previous_track()
    elif any(w in cmd for w in ["volume up", "louder", "increase"]):
        music_player.increase_volume()
    elif any(w in cmd for w in ["volume down", "softer", "decrease"]):
        music_player.decrease_volume()
    elif any(w in cmd for w in ["play", "start"]):
        music_player.play_random_music()

@on_fuzzy(["what's playing", "current track", "which song is this", "what song is playing"], score_cutoff=90)
def handle_current_track_query():
    cur = music_player.get_current_track()
    if cur:
        speak(f"Currently playing: {cur}")
    else:
        speak("No music is currently playing")

@on_fuzzy(["current location", "where am i", "my location", "where am I right now"], score_cutoff=90)
def handle_location():
    get_current_location()

@on_regex(r"\bplay\s+(.*?)\s+(?:on\s+youtube|youtube)$")
def handle_youtube_play(q):
    play_on_youtube(q)

# Consolidated into handle_unified_search

@on_fuzzy(["previous video", "last video", "go back video"], score_cutoff=90)
def handle_yt_prev():
    previous_video()

@on_fuzzy(["next video", "skip to next video"], score_cutoff=90)
def handle_yt_next():
    next_video()

@on_fuzzy(["pause video", "pause the video"], score_cutoff=90)
def handle_yt_pause():
    pause_youtube()

@on_fuzzy(["replay video", "replay the video", "play video again"], score_cutoff=90)
def handle_yt_replay():
    replay_video()

@on_regex(r"\b(?:resume|play)\s+(?:the\s+)?video")
def handle_yt_resume():
    resume_youtube()

@on_regex(r"(?P<action>mute|unmute)\s+(?:the\s+)?video")
@on_fuzzy(["mute video", "mute the video", "unmute video", "unmute the video"], score_cutoff=90)
def handle_yt_mute_toggle(text=None, action=None):
    cmd = (action or text or "").lower()
    if "unmute" in cmd:
        unmute_youtube()
    else:
        mute_youtube()

@on_regex(r"(?:turn\s+(?P<state>on|off)\s+)?subtitles?\s*(?P<state2>on|off)?")
def handle_yt_subtitles(text=None, state=None, state2=None):
    s = (state or state2 or text or "").lower()
    if any(w in s for w in ["on", "enable", "turn on"]):
        turn_on_subtitles()
    else:
        turn_off_subtitles()

@on_regex(r"\b(?:volume\s+(?:up|down)|(?:increase|decrease)\s+(?:the\s+)?volume).*video", priority=1)
def handle_yt_volume(text):
    if any(w in text for w in ["up", "increase"]):
        control_youtube_video("volume increase")
    else:
        control_youtube_video("volume decrease")

@on_fuzzy(["skip backward", "rewind video", "go back in video"], score_cutoff=90)
def handle_yt_skip_back():
    skip_backward_video()

@on_fuzzy(["skip video", "skip forward", "fast forward video"], score_cutoff=90)
def handle_yt_skip_fwd():
    skip_video()

@on_regex(r"\b(?P<action>increase|decrease|raise|lower|turn up|turn down|up|down)\b\s*(?:the\s+)?volume")
@on_fuzzy(["increase volume", "volume up", "make it louder", "louder", "up the volume",
           "decrease volume", "volume down", "make it softer", "softer", "lower volume",
           "down the volume", "mute", "mute volume", "turn sound off",
           "unmute", "unmute volume", "turn sound on"], score_cutoff=90)
def handle_system_volume(text=None, action=None):
    cmd = (action or text or "").lower()
    if any(w in cmd for w in ["unmute", "sound on"]):
        ui.hotkey("volumemute")
        speak("Volume unmuted")
    elif any(w in cmd for w in ["mute", "sound off"]):
        speak("Muting volume")
        ui.press("volumemute")
    elif any(w in cmd for w in ["increase", "raise", "turn up", "up", "louder"]):
        handle_volume_change("increase")
    else:
        handle_volume_change("decrease")

@on_regex(r"search\s+(?:the\s+web\s+for\s+|web\s+for\s+|for\s+)?(?P<query>.*?)(?:\s+(?:on|in|from)\s+(?P<provider>google|youtube|wikipedia|wiki))?$", priority=2)
def handle_unified_search(query, provider=None):
    """
    Unified search handler that routes queries to the correct provider.
    Priority: Explicit Provider > Web/Google Fallback.
    """
    p = (provider or "").lower()
    q = query.strip()

    if p == "youtube":
        speak(f"Searching for {q} on YouTube")
        search_on_youtube(q)
    elif p in ["wikipedia", "wiki"]:
        speak(f"Searching Wikipedia for {q}")
        wiki_search(q)
    elif p == "google":
        speak(f"Searching Google for {q}")
        handle_web_search(q)
    else:
        # No explicit provider or just "web"
        speak(f"Searching the web for {q}. Please wait a moment...")
        generate(user_prompt=q, prints=True)

@on_fuzzy(["what time", "what time is it", "current time", "what's the time", "tell me the time"], score_cutoff=90)
def handle_time_query():
    tell_time()

@on_fuzzy(["what date", "what's the date", "current date", "tell me the date"], score_cutoff=90)
def handle_date_query():
    tell_date()

@on_fuzzy(["tell a joke", "tell me a joke", "make me laugh", "a joke"], score_cutoff=90)
def handle_joke_cmd():
    tell_joke()

@on_fuzzy(["system info", "system status", "computer info"], score_cutoff=90)
def handle_sys_info():
    get_system_info()

@on_fuzzy(["battery percentage", "battery status", "check battery"], score_cutoff=90)
def handle_battery_stat():
    battery_monitor.battery_percentage()

@on_fuzzy(["check ip address", "check my ip address", "what is my ip"], score_cutoff=90)
def handle_ip_check():
    check_ip_address()

@on_fuzzy(["check running apps", "check the running apps", "what is running"], score_cutoff=90)
def handle_running_apps():
    check_running_app()

@on_regex(r"(?:please\s+)?(?:create|generate)(?:\s+an)?\s+image\s+of\s+(?P<prompt>.*)$")
def handle_image_gen(prompt):
    speak(f"Generating image of {prompt}. Please wait a moment...")
    generate_image_from_text(prompt)

@on_fuzzy(["check temperature", "check the temperature", "what is the temperature"], score_cutoff=90)
def handle_temp():
    speak("Checking the temperature. Please wait a moment...")
    get_current_temperature()

@on_regex(r"(?:check\s+(?:the\s+)?)?weather$")
@on_fuzzy(["what's the weather today", "check today's weather", "today's weather", "weather today", "check the weather"], score_cutoff=90)
def handle_weather_today():
    speak("Checking Today's weather conditions. Please wait a moment...")
    get_overall_weather()

@on_regex(r"(?:check\s+the\s+)?weather\s+(?:in|for|at|of)\s+(?P<location>.*)$")
def handle_weather_location(location):
    speak(f"Checking the weather in {location}. Please wait a moment...")
    get_weather_by_address(address=location)

@on_fuzzy(["tell me news", "what's the news", "today's news", "latest news", "news headlines", "top headlines", "current news"], score_cutoff=90)
def handle_news_cmd():
    tell_news()

@on_regex(r"remember\s+that\s+(?P<text>.*)$")
def handle_remember(text):
    remember_info(text)

@on_fuzzy(["what did i ask you to remember", "what do you remember", "recall"], score_cutoff=90)
def handle_recall():
    recall_info()

@on_fuzzy(["shutdown", "shut down", "turn off computer"], score_cutoff=90)
def handle_shutdown_cmd():
    speak("Shutting down the system in 10 seconds")
    os.system("shutdown /s /t 10")

@on_fuzzy(["restart", "restart computer", "reboot"], score_cutoff=90)
def handle_restart_cmd():
    speak("Restarting the system in 10 seconds")
    os.system("shutdown /r /t 10")


def process_command(normalized_text):
    """
    Process and execute voice commands using a modular registry system.
    """
    start_time = time.time()
    try:
        if not normalized_text:
            welcome()
            return

        # Attempt to execute command from registry
        if not cmd_registry.execute(normalized_text):
            # Fallback to AI brain for unrecognized commands
            brain(normalized_text)
    except Exception as e:
        print(f"Error in process_command: {e}")
        speak("I had trouble understanding or executing that command.")
    finally:
        from assistant.core.ear import recognizer
        actual_start = getattr(recognizer, 'last_recognition_time', start_time)
        execution_time = time.time() - actual_start
        print(f"[Timer] Command executed in {execution_time:.2f} seconds.")
        # Reset to avoid reusing the same timestamp for subsequent immediate calls
        recognizer.last_recognition_time = time.time()


if __name__ == "__main__":
    pass
