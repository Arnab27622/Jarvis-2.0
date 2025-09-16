import re
from urllib.parse import quote
import webbrowser
from assistant.core.speak_selector import speak
import random
from data.dlg_data.dlg import search_result


def handle_web_search(command_text):
    """Perform a web search"""
    search_query = re.sub(
        r"\b(search|find|look up|for|in|on|google|web)\b",
        "",
        command_text,
        flags=re.IGNORECASE,
    ).strip()

    search_query = re.sub(r"\s+", " ", search_query).strip()

    if search_query:
        encoded_query = quote(search_query)
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        speak(f"{random.choice(search_result)} {search_query}")
    else:
        speak("What would you like me to search for?")
