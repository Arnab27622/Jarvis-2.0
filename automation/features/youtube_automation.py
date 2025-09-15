from dotenv import load_dotenv
from head.speak_selector import speak
import os
import webbrowser
from urllib.parse import quote
from googleapiclient.discovery import build


load_dotenv()


def play_on_youtube(search_query):
    """Play videos on YouTube using the official API"""
    try:
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
