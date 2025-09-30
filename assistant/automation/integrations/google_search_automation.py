import re
from urllib.parse import quote
import webbrowser
from assistant.core.speak_selector import speak
import random
from data.dlg_data.dlg import search_result


def handle_web_search(command_text):
    """
    Perform a web search by extracting the search query from voice commands.
    
    This function processes natural language voice commands to extract the
    core search query, then opens a Google search in the default web browser
    with the properly encoded search terms.
    
    Args:
        command_text (str): The voice command containing search instructions.
                          Examples: "search for Python tutorials", 
                          "look up weather in London", "find restaurants near me"
    
    Process:
        1. Removes common search-related verbs and prepositions using regex
        2. Cleans up extra whitespace
        3. URL-encodes the search query for web safety
        4. Opens Google search in default browser
        5. Provides voice confirmation with random dialogue
    
    Example:
        >>> handle_web_search("search for Python programming tutorials")
        # Opens: https://www.google.com/search?q=Python%20programming%20tutorials
        # Speaks: "Here's what I found for Python programming tutorials"
    
    Note:
        The regex pattern removes common search verbs and platform names but
        preserves the core search intent. Multiple spaces are collapsed to
        ensure clean URL encoding.
    """
    # Remove common search-related words using regex pattern matching
    search_query = re.sub(
        r"\b(search|find|look up|for|in|on|google|web)\b",
        "",
        command_text,
        flags=re.IGNORECASE,
    ).strip()

    # Clean up any extra whitespace that may have been introduced
    search_query = re.sub(r"\s+", " ", search_query).strip()

    if search_query:
        # URL encode the search query to handle special characters safely
        encoded_query = quote(search_query)
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        speak(f"{random.choice(search_result)} {search_query}")
    else:
        speak("What would you like me to search for?")


if __name__ == "__main__":
    """
    Test function for the web search automation.
    
    When run as a standalone script, this tests the web search functionality
    with a sample search query to verify the system is working correctly.
    """
    handle_web_search("aws")