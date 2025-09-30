import requests
import random
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from assistant.core.speak_selector import speak

# Cache to store recent advice to avoid repeated API calls
advice_cache = []
CACHE_SIZE = 5
LAST_API_CALL = 0
API_COOLDOWN = 30  # seconds between API calls


def fetch_advice_slip() -> Optional[str]:
    """
    Fetch random advice from the AdviceSlip API.
    
    Makes a GET request to the AdviceSlip API and extracts the advice text
    from the JSON response.
    
    Returns:
        Optional[str]: Advice string if successful, None if request fails
    """
    try:
        response = requests.get("https://api.adviceslip.com/advice", timeout=2)
        response.raise_for_status()
        data = response.json()
        return data["slip"]["advice"]
    except:
        return None


def fetch_zen_quotes() -> Optional[str]:
    """
    Fetch random quote from the ZenQuotes API.
    
    Makes a GET request to the ZenQuotes API and formats the quote with author.
    
    Returns:
        Optional[str]: Formatted quote string (quote + author) if successful, 
                      None if request fails
    """
    try:
        response = requests.get("https://zenquotes.io/api/random", timeout=2)
        response.raise_for_status()
        data = response.json()
        return f"{data[0]['q']} - {data[0]['a']}"
    except:
        return None


def rand_advice() -> Optional[str]:
    """
    Fetch random advice from multiple APIs with intelligent fallback strategy.
    
    This function attempts to fetch advice from external APIs concurrently.
    If APIs are unavailable or slow, it uses cached responses or local fallback advice.
    
    Strategy:
    1. First checks cache if recent API call was made (within cooldown period)
    2. Attempts concurrent API calls to multiple advice services
    3. Falls back to local advice list if all APIs fail
    4. Updates cache with successful API responses
    
    Returns:
        Optional[str]: A piece of advice, quote, or motivational statement.
                      Returns None only if all fallbacks fail (unlikely due to local list).
    """
    global LAST_API_CALL, advice_cache

    # Local fallback advice - used when all APIs are unavailable
    fallback_advice = [
        "The best time to plant a tree was 20 years ago. The second best time is now.",
        "Code is like humor. When you have to explain it, it's bad.",
        "The only way to do great work is to love what you do.",
        "First, solve the problem. Then, write the code.",
        "The most disastrous thing that you can ever learn is your first programming language.",
        "Debugging is like being a detective in a crime movie where you are also the murderer.",
        "The best error message is the one that never shows up.",
        "Don't comment bad code - rewrite it.",
        "Simplicity is the soul of efficiency.",
        "Make it work, make it right, make it fast.",
    ]

    # Return cached advice if we have it and API calls are too frequent
    current_time = time.time()
    if advice_cache and current_time - LAST_API_CALL < API_COOLDOWN:
        return random.choice(advice_cache)

    # Try to get advice from APIs concurrently for better performance
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit API calls to thread pool
        future_to_api = {
            executor.submit(fetch_advice_slip): "AdviceSlip",
            executor.submit(fetch_zen_quotes): "ZenQuotes",
        }

        # Process completed API calls as they finish (with 3 second timeout)
        for future in as_completed(future_to_api, timeout=3):
            try:
                advice = future.result()
                if advice:
                    # Add to cache (FIFO if cache is full)
                    if len(advice_cache) >= CACHE_SIZE:
                        advice_cache.pop(0)
                    advice_cache.append(advice)
                    LAST_API_CALL = current_time
                    print(f"Successfully fetched advice from {future_to_api[future]}")
                    return advice
            except:
                continue  # If one API fails, try the next one

    # If all APIs fail, use local fallback advice
    print("All advice APIs failed, using local fallback")
    return random.choice(fallback_advice)


# Example usage
if __name__ == "__main__":
    """
    Test the advice functionality when run as a standalone script.
    """
    advice = rand_advice()
    if advice:
        speak(advice)
    else:
        speak("Failed to get advice")