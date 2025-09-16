from dotenv import load_dotenv
from assistant.core.speak_selector import speak
import os
import webbrowser
from urllib.parse import quote
import pyautogui as ui
import time
import pygetwindow as gw


load_dotenv()


# Global variables for YouTube player control
youtube_player_state = {
    "is_playing": False,
    "is_muted": False,
    "current_volume": 100,
    "current_video_id": None,
}


def activate_youtube_window(timeout=5):
    """
    Attempt to activate a window with 'youtube' in its title.
    If multiple found, activate the first one.
    Wait briefly for focus, return True if successful.
    """
    try:
        all_windows = gw.getAllWindows()
        youtube_windows = [
            w for w in all_windows if w.title and "youtube" in w.title.lower()
        ]
        if not youtube_windows:
            print("No YouTube window found to activate.")
            return False
        youtube_windows[0].activate()
        time.sleep(2)  # give time for window to become active
        return True
    except Exception as e:
        print(f"Failed to activate YouTube window: {e}")
        return False


def play_on_youtube(search_query):
    """Play videos on YouTube using the official API"""
    try:
        from googleapiclient.discovery import build
        remove_words = ["play", "youtube", "on", "jarvis"]
        for word in remove_words:
            search_query = search_query.replace(word, "")
        search_query = search_query.strip()

        if not search_query:
            speak("What would you like me to play on YouTube?")
            return

        YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

        if not YOUTUBE_API_KEY:
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(f"Showing results for {search_query} on YouTube")
            return

        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        request = youtube.search().list(
            part="snippet", maxResults=1, q=search_query, type="video"
        )
        response = request.execute()

        if response["items"]:
            video_id = response["items"][0]["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            speak(f"Playing {search_query} on YouTube")
            webbrowser.open(video_url)
            youtube_player_state["current_video_id"] = video_id
            time.sleep(5)
            ui.hotkey("alt", "tab")
        else:
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(
                f"No videos found for {search_query}. Showing search results instead."
            )

    except Exception as e:
        print(f"Error with YouTube API: {e}")
        encoded_query = quote(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        speak(f"Showing results for {search_query} on YouTube")


def search_on_youtube(search_query):
    """Search videos on YouTube using the official API"""
    remove_words = ["youtube", "search", "for", "on", "jarvis"]

    for word in remove_words:
        search_query = search_query.replace(word, "")

    search_query = search_query.strip()

    if not search_query:
        speak("What would you like me to search on YouTube?")
        return

    encoded_query = quote(search_query)
    url = f"https://www.youtube.com/results?search_query={encoded_query}"
    webbrowser.open(url)
    speak(f"Showing results for {search_query} on YouTube")


def control_youtube_video(action):
    """
    Control YouTube video playback using keyboard shortcuts.
    Actions: play, pause, mute, unmute, volume, replay, stop
    """
    try:
        # Focus on the YouTube browser window first
        if not activate_youtube_window():
            speak("Could not find an active YouTube window to control.")
            return

        time.sleep(0.5)

        if action == "play" or action == "resume":
            speak("Playing the video...")
            ui.press("k")
            youtube_player_state["is_playing"] = True

        elif action == "pause":
            ui.press("k")
            youtube_player_state["is_playing"] = False
            speak("Video paused")

        elif action == "mute":
            ui.press("m")  # Mute toggle in YouTube
            youtube_player_state["is_muted"] = True
            speak("Video muted")

        elif action == "unmute":
            speak("Unmuting the video...")
            ui.press("m")  # Mute toggle in YouTube
            youtube_player_state["is_muted"] = False

        elif action == "volume increase":
            ui.press("up")
            youtube_player_state["current_volume"] = min(
                youtube_player_state["current_volume"] + 5, 100
            )
            speak(f"Volume increased to {youtube_player_state['current_volume']}%")

        elif action == "volume decrease":
            ui.press("down")
            youtube_player_state["current_volume"] = max(
                youtube_player_state["current_volume"] - 5, 0
            )
            speak(f"Volume decreased to {youtube_player_state['current_volume']}%")

        elif action == "skip":
            ui.press("l")  # Skip forward 10 seconds in YouTube
            speak("Skipped forward")

        elif action == "skip backward":
            ui.press("j")  # Skip backward 10 seconds in YouTube
            speak("Skipped backward")

        elif action == "previous video":
            speak("Playing previous video...")
            ui.hotkey("shift", "p")  # Previous video in playlist (if available)

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


def set_volume(volume_level):
    """Set volume level (0-100) - approximate via multiple volume up/down presses"""
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


def mute_youtube():
    """Mute YouTube video"""
    control_youtube_video("mute")


def unmute_youtube():
    """Unmute YouTube video"""
    control_youtube_video("unmute")


def pause_youtube():
    """Pause YouTube video"""
    control_youtube_video("pause")


def resume_youtube():
    """Resume YouTube video"""
    control_youtube_video("play")


def skip_video():
    """Skip forward the video by 10 seconds"""
    control_youtube_video("skip")


def skip_backward_video():
    """Skip backward the video by 10 seconds"""
    control_youtube_video("skip backward")


def next_video():
    """Skip to next video in queue"""
    control_youtube_video("next video")


def previous_video():
    """Go to previous video in queue"""
    control_youtube_video("previous video")


def replay_video():
    """Replay the current video from the start"""
    control_youtube_video("replay")


def turn_on_subtitles():
    """Turn on subtitles"""
    control_youtube_video("subtitles on")


def turn_off_subtitles():
    """Turn off subtitles"""
    control_youtube_video("subtitles off")


def fullscreen_youtube():
    "Full screen the video"
    control_youtube_video("turn on fullscreen")


def exit_fullscreen_youtube():
    "Exit the Full screen"
    control_youtube_video("turn off fullscreen")
