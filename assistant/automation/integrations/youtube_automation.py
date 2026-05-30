"""Module for automating YouTube interactions, including playback control and search."""

import webbrowser
import time
import re
from urllib.parse import quote
import pyautogui as ui
import pygetwindow as gw
from assistant.core.config import config
from assistant.automation.features.window_automation import toggle_fullscreen
from assistant.core.speak_selector import speak
from assistant.core.registry import on_regex, on_fuzzy

youtube_player_state = {
    "is_playing": False,
    "is_muted": False,
    "current_volume": 100,
    "current_video_id": None,
}

def activate_youtube_window(timeout: int = 5) -> bool:
    """Brings the active YouTube browser window to the foreground."""
    try:
        all_windows = gw.getAllWindows()
        youtube_windows = [
            w for w in all_windows if w.title and "youtube" in w.title.lower()
        ]
        if not youtube_windows:
            print("No YouTube window found to activate.")
            return False
        youtube_windows[0].activate()
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Failed to activate YouTube window: {e}")
        return False

def play_on_youtube(search_query: str) -> None:
    """Searches for and plays a video or playlist on YouTube."""
    try:
        from googleapiclient.discovery import build
        
        remove_words = ["play", "youtube", "on", "jarvis"]
        for word in remove_words:
            search_query = re.sub(rf'\b{word}\b', '', search_query, flags=re.IGNORECASE).strip()

        if not search_query:
            speak("What would you like me to play on YouTube?")
            return

        YOUTUBE_API_KEY = config.youtube_api_key

        if not YOUTUBE_API_KEY:
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(f"Showing results for {search_query} on YouTube")
            return

        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(part="snippet", maxResults=1, q=search_query, type="video,playlist")
        response = request.execute()

        if response.get("items"):
            item = response["items"][0]
            item_id = item["id"]
            
            if item_id["kind"] == "youtube#playlist":
                playlist_id = item_id["playlistId"]
                video_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                speak(f"Playing {search_query} playlist on YouTube")
                youtube_player_state["current_video_id"] = playlist_id
            else:
                video_id = item_id["videoId"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                speak(f"Playing {search_query} on YouTube")
                youtube_player_state["current_video_id"] = video_id
                
            webbrowser.open(video_url)
            time.sleep(5)
            ui.hotkey("alt", "tab")
        else:
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(f"No videos found for {search_query}. Showing search results instead.")

    except Exception as e:
        print(f"Error with YouTube API: {e}")
        encoded_query = quote(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        speak(f"Showing results for {search_query} on YouTube")

def search_on_youtube(search_query: str) -> None:
    """Opens a YouTube search results page for the given query."""
    remove_words = ["youtube", "search", "for", "on", "jarvis"]
    for word in remove_words:
        search_query = re.sub(rf'\b{word}\b', '', search_query, flags=re.IGNORECASE).strip()

    if not search_query:
        speak("What would you like me to search on YouTube?")
        return

    encoded_query = quote(search_query)
    url = f"https://www.youtube.com/results?search_query={encoded_query}"
    webbrowser.open(url)
    speak(f"Showing results for {search_query} on YouTube")

def control_youtube_video(action: str) -> None:
    """Executes keyboard shortcuts to control YouTube playback."""
    try:
        if not activate_youtube_window():
            speak("Could not find an active YouTube window to control.")
            return

        time.sleep(0.5)

        if action in ["play", "resume"]:
            speak("Playing the video...")
            ui.press("k")
            youtube_player_state["is_playing"] = True

        elif action == "pause":
            ui.press("k")
            youtube_player_state["is_playing"] = False
            speak("Video paused")

        elif action == "mute":
            ui.press("m")
            youtube_player_state["is_muted"] = True
            speak("Video muted")

        elif action == "unmute":
            speak("Unmuting the video...")
            ui.press("m")
            youtube_player_state["is_muted"] = False

        elif action == "volume increase":
            ui.press("up")
            youtube_player_state["current_volume"] = min(youtube_player_state["current_volume"] + 5, 100)
            speak(f"Volume increased to {youtube_player_state['current_volume']}%")

        elif action == "volume decrease":
            ui.press("down")
            youtube_player_state["current_volume"] = max(youtube_player_state["current_volume"] - 5, 0)
            speak(f"Volume decreased to {youtube_player_state['current_volume']}%")

        elif action == "skip":
            ui.press("l")
            speak("Skipped forward")

        elif action == "skip backward":
            ui.press("j")
            speak("Skipped backward")

        elif action == "previous video":
            speak("Playing previous video...")
            ui.hotkey("shift", "p")

        elif action == "next video":
            speak("Playing next video...")
            ui.hotkey("shift", "n")

        elif action == "replay":
            speak("Replaying the video...")
            ui.press("0")
            ui.press("k")

        elif action == "subtitles on":
            speak("Turning on the subtitles...")
            ui.press("c")

        elif action == "subtitles off":
            speak("Turning off the subtitles...")
            ui.press("c")

        elif action == "turn on fullscreen":
            speak("Making the video full screen...")
            ui.press("f")

        elif action == "turn off fullscreen":
            speak("Exiting the full screen...")
            ui.press("f")

        else:
            speak("Action not recognized")
    except Exception as e:
        print(f"Error controlling YouTube video: {e}")
        speak("Sorry, I couldn't control the video")

def set_volume(volume_level: int) -> None:
    """Adjusts the YouTube volume to a specific percentage."""
    current = youtube_player_state["current_volume"]
    if volume_level < 0 or volume_level > 100:
        speak("Volume level must be between 0 and 100")
        return
    difference = volume_level - current
    if difference == 0:
        speak("Volume is already at the requested level")
        return
    elif difference > 0:
        for _ in range(difference // 5):
            control_youtube_video("volume increase")
            time.sleep(0.1)
    else:
        for _ in range(abs(difference) // 5):
            control_youtube_video("volume decrease")
            time.sleep(0.1)

@on_regex(r"(?P<text>.*(?:full\s*screen|fullscreen).*)$")
def handle_fullscreen_logic(text):
    if "video" in text:
        control_youtube_video("turn on fullscreen")
    else:
        toggle_fullscreen()

@on_regex(r"turn\s+off\s+full\s*screen.*video")
def handle_video_exit_fullscreen():
    control_youtube_video("turn off fullscreen")

@on_regex(r"\bplay\s+(.*?)\s+(?:on\s+youtube|youtube)$")
def handle_youtube_play(q):
    play_on_youtube(q)

@on_fuzzy(["previous video", "last video", "go back video"], score_cutoff=90)
def handle_yt_prev():
    control_youtube_video("previous video")

@on_fuzzy(["next video", "skip to next video"], score_cutoff=90)
def handle_yt_next():
    control_youtube_video("next video")

@on_fuzzy(["pause video", "pause the video"], score_cutoff=90)
def handle_yt_pause():
    control_youtube_video("pause")

@on_fuzzy(["replay video", "replay the video", "play video again"], score_cutoff=90)
def handle_yt_replay():
    control_youtube_video("replay")

@on_regex(r"\b(?:resume|play)\s+(?:the\s+)?video")
def handle_yt_resume():
    control_youtube_video("resume")

@on_regex(r"(?P<action>mute|unmute)\s+(?:the\s+)?video")
@on_fuzzy(["mute video", "mute the video", "unmute video", "unmute the video"], score_cutoff=90)
def handle_yt_mute_toggle(text=None, action=None):
    cmd = (action or text or "").lower()
    if "unmute" in cmd:
        control_youtube_video("unmute")
    else:
        control_youtube_video("mute")

@on_regex(r"(?:turn\s+(?P<state>on|off)\s+)?subtitles?\s*(?P<state2>on|off)?")
def handle_yt_subtitles(text=None, state=None, state2=None):
    s = (state or state2 or text or "").lower()
    if any(w in s for w in ["on", "enable", "turn on"]):
        control_youtube_video("subtitles on")
    else:
        control_youtube_video("subtitles off")

@on_regex(r"\b(?:volume\s+(?:up|down)|(?:increase|decrease)\s+(?:the\s+)?volume).*video", priority=1)
def handle_yt_volume(text):
    if any(w in text for w in ["up", "increase"]):
        control_youtube_video("volume increase")
    else:
        control_youtube_video("volume decrease")

@on_fuzzy(["skip backward", "rewind video", "go back in video"], score_cutoff=90)
def handle_yt_skip_back():
    control_youtube_video("skip backward")

@on_fuzzy(["skip video", "skip forward", "fast forward video"], score_cutoff=90)
def handle_yt_skip_fwd():
    control_youtube_video("skip")
