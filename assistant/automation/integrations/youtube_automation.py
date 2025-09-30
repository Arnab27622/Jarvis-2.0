from dotenv import load_dotenv
from assistant.core.speak_selector import speak
import os
import webbrowser
from urllib.parse import quote
import pyautogui as ui
import time
import pygetwindow as gw

# Load environment variables from .env file for API key security
load_dotenv()

# Global state tracker for YouTube player control
# This maintains the current state of YouTube playback across function calls
youtube_player_state = {
    "is_playing": False,  # Current playback status (playing/paused)
    "is_muted": False,  # Current mute status
    "current_volume": 100,  # Current volume level (0-100)
    "current_video_id": None,  # Currently playing video ID for tracking
}


def activate_youtube_window(timeout=5):
    """
    Activate a YouTube browser window by searching for windows with 'youtube' in the title.

    This function scans all open windows to find browser windows with YouTube content
    and brings the first matching window to the foreground for keyboard control.

    Args:
        timeout (int): Maximum time to wait for window activation (default: 5 seconds)

    Returns:
        bool: True if a YouTube window was found and activated successfully, False otherwise

    Process:
        1. Retrieve all open windows using pygetwindow
        2. Filter windows containing 'youtube' in the title (case-insensitive)
        3. Activate the first matching window
        4. Wait for window focus stabilization

    Note:
        This function relies on window titles containing 'youtube', which works for
        most browsers but may fail if the window title doesn't match this pattern.
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
    """
    Play videos on YouTube using the official YouTube Data API with fallback to direct search.

    This function provides intelligent video playback by first attempting to use the
    YouTube Data API for precise video matching, then falling back to direct YouTube
    search if the API is unavailable or fails.

    Args:
        search_query (str): The video title or search terms to play on YouTube

    Process:
        1. Clean the search query by removing command words
        2. Check for YouTube API key availability
        3. If API available: search for exact video and play directly
        4. If API unavailable: open YouTube search results in browser
        5. Update global player state with current video information

    API Features:
        - Uses YouTube Data API v3 for precise video matching
        - Returns the most relevant video result
        - Direct video URL generation for immediate playback

    Fallback Strategy:
        - If API key missing: direct YouTube search
        - If API call fails: direct YouTube search
        - If no results found: direct YouTube search

    Example:
        >>> play_on_youtube("play never gonna give you up")
        # Opens: https://www.youtube.com/watch?v=dQw4w9WgXcQ
        # Speaks: "Playing never gonna give you up on YouTube"
    """
    try:
        from googleapiclient.discovery import build

        # Remove common command words to extract the core search query
        remove_words = ["play", "youtube", "on", "jarvis"]
        for word in remove_words:
            search_query = search_query.replace(word, "")
        search_query = search_query.strip()

        if not search_query:
            speak("What would you like me to play on YouTube?")
            return

        YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

        # Fallback to direct search if API key not available
        if not YOUTUBE_API_KEY:
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(f"Showing results for {search_query} on YouTube")
            return

        # Initialize YouTube Data API client
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        # Execute search for videos
        request = youtube.search().list(
            part="snippet", maxResults=1, q=search_query, type="video"
        )
        response = request.execute()

        if response["items"]:
            # Extract video ID from the first search result
            video_id = response["items"][0]["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            speak(f"Playing {search_query} on YouTube")
            webbrowser.open(video_url)
            youtube_player_state["current_video_id"] = video_id
            time.sleep(5)
            ui.hotkey("alt", "tab")  # Switch back to previous window
        else:
            # No results found via API, fallback to direct search
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(
                f"No videos found for {search_query}. Showing search results instead."
            )

    except Exception as e:
        print(f"Error with YouTube API: {e}")
        # Fallback to direct search on any exception
        encoded_query = quote(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        speak(f"Showing results for {search_query} on YouTube")


def search_on_youtube(search_query):
    """
    Search for videos on YouTube without automatic playback.

    This function performs a YouTube search and displays the results page,
    allowing users to browse and select from multiple videos rather than
    automatically playing the first result.

    Args:
        search_query (str): The search terms to look up on YouTube

    Process:
        1. Clean the search query by removing command words
        2. URL-encode the search query for web safety
        3. Open YouTube search results in the default browser
        4. Provide voice confirmation of the action

    Example:
        >>> search_on_youtube("search for python tutorials on youtube")
        # Opens: https://www.youtube.com/results?search_query=python%20tutorials
        # Speaks: "Showing results for python tutorials on YouTube"
    """
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
    Control YouTube video playback using keyboard shortcuts and global state tracking.

    This function provides comprehensive YouTube player control by sending keyboard
    shortcuts to an active YouTube window and maintaining consistent state tracking.

    Args:
        action (str): The playback control action to perform. Supported actions:
                    - "play" / "resume": Start or resume playback (K key)
                    - "pause": Pause playback (K key)
                    - "mute": Mute audio (M key)
                    - "unmute": Unmute audio (M key)
                    - "volume increase": Increase volume (Up arrow)
                    - "volume decrease": Decrease volume (Down arrow)
                    - "skip": Skip forward 10 seconds (L key)
                    - "skip backward": Skip backward 10 seconds (J key)
                    - "previous video": Previous video in playlist (Shift+P)
                    - "next video": Next video in playlist (Shift+N)
                    - "replay": Restart current video (0 + K keys)
                    - "subtitles on": Enable subtitles (C key)
                    - "subtitles off": Disable subtitles (C key)
                    - "turn on fullscreen": Enter fullscreen (F key)
                    - "turn off fullscreen": Exit fullscreen (F key)

    Process:
        1. Attempt to activate a YouTube window
        2. Send appropriate keyboard shortcuts for the requested action
        3. Update global player state accordingly
        4. Provide voice confirmation to user

    YouTube Shortcuts Reference:
        - K: Play/Pause toggle
        - M: Mute/Unmute toggle
        - L: Forward 10 seconds
        - J: Backward 10 seconds
        - F: Fullscreen toggle
        - C: Closed captions toggle
        - 0: Seek to beginning
        - Shift+P: Previous video
        - Shift+N: Next video

    Note:
        Requires an active YouTube window in a supported browser.
        Some shortcuts may vary by browser or YouTube interface version.
    """
    try:
        # Focus on the YouTube browser window first
        if not activate_youtube_window():
            speak("Could not find an active YouTube window to control.")
            return

        time.sleep(0.5)  # Brief pause for window stabilization

        if action == "play" or action == "resume":
            speak("Playing the video...")
            ui.press("k")  # YouTube play/pause toggle
            youtube_player_state["is_playing"] = True

        elif action == "pause":
            ui.press("k")  # YouTube play/pause toggle
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
            ui.press("up")  # Volume up in YouTube
            youtube_player_state["current_volume"] = min(
                youtube_player_state["current_volume"] + 5, 100
            )
            speak(f"Volume increased to {youtube_player_state['current_volume']}%")

        elif action == "volume decrease":
            ui.press("down")  # Volume down in YouTube
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
            ui.hotkey("shift", "n")  # Next video in playlist

        elif action == "replay":
            speak("Replaying the video...")
            ui.press("0")  # Seek to beginning
            ui.press("k")  # Play

        elif action == "subtitles on":
            speak("Turning on the subtitles...")
            ui.press("c")  # Closed captions toggle

        elif action == "subtitles off":
            speak("Turning off the subtitles...")
            ui.press("c")  # Closed captions toggle

        elif action == "turn on fullscreen":
            speak("Making the video full screen...")
            ui.press("f")  # Fullscreen toggle

        elif action == "turn off fullscreen":
            speak("Exiting the full screen...")
            ui.press("f")  # Fullscreen toggle

        else:
            speak("Action not recognized")
    except Exception as e:
        print(f"Error controlling YouTube video: {e}")
        speak("Sorry, I couldn't control the video")


def set_volume(volume_level):
    """
    Set YouTube volume to a specific level using incremental adjustments.

    This function achieves precise volume control by sending multiple volume
    adjustment commands to reach the target volume level from the current level.

    Args:
        volume_level (int): Target volume level between 0 and 100

    Process:
        1. Validate volume level range
        2. Calculate difference from current volume
        3. Send multiple volume up/down commands in 5% increments
        4. Update global volume state

    Note:
        YouTube doesn't support direct volume setting via keyboard, so this
        function uses incremental adjustments which may take several seconds
        for large volume changes.
    """
    current = youtube_player_state["current_volume"]
    if volume_level < 0 or volume_level > 100:
        speak("Volume level must be between 0 and 100")
        return
    difference = volume_level - current
    if difference == 0:
        speak("Volume is already at the requested level")
        return
    elif difference > 0:
        # Increase volume in 5% increments
        for _ in range(difference // 5):
            control_youtube_video("volume increase")
            time.sleep(0.1)  # Brief pause between commands
    else:
        # Decrease volume in 5% increments
        for _ in range(abs(difference) // 5):
            control_youtube_video("volume decrease")
            time.sleep(0.1)  # Brief pause between commands


# Convenience functions for common YouTube control actions


def mute_youtube():
    """Mute YouTube video audio."""
    control_youtube_video("mute")


def unmute_youtube():
    """Unmute YouTube video audio."""
    control_youtube_video("unmute")


def pause_youtube():
    """Pause YouTube video playback."""
    control_youtube_video("pause")


def resume_youtube():
    """Resume YouTube video playback."""
    control_youtube_video("play")


def skip_video():
    """Skip forward in YouTube video by 10 seconds."""
    control_youtube_video("skip")


def skip_backward_video():
    """Skip backward in YouTube video by 10 seconds."""
    control_youtube_video("skip backward")


def next_video():
    """Skip to next video in YouTube playlist or queue."""
    control_youtube_video("next video")


def previous_video():
    """Go to previous video in YouTube playlist or queue."""
    control_youtube_video("previous video")


def replay_video():
    """Restart current YouTube video from the beginning."""
    control_youtube_video("replay")


def turn_on_subtitles():
    """Enable closed captions/subtitles for YouTube video."""
    control_youtube_video("subtitles on")


def turn_off_subtitles():
    """Disable closed captions/subtitles for YouTube video."""
    control_youtube_video("subtitles off")


def fullscreen_youtube():
    """Enter fullscreen mode for YouTube video."""
    control_youtube_video("turn on fullscreen")


def exit_fullscreen_youtube():
    """Exit fullscreen mode for YouTube video."""
    control_youtube_video("turn off fullscreen")
