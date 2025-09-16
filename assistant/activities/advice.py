import requests
import random
import sys
import time
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from assistant.core.speak_selector import speak

# Cache to store recent advice to avoid repeated API calls
advice_cache = []
CACHE_SIZE = 5
LAST_API_CALL = 0
API_COOLDOWN = 30  # seconds between API calls


def fetch_advice_slip() -> Optional[str]:
    """Fetch advice from AdviceSlip API"""
    try:
        response = requests.get("https://api.adviceslip.com/advice", timeout=2)
        response.raise_for_status()
        data = response.json()
        return data["slip"]["advice"]
    except:
        return None


def fetch_zen_quotes() -> Optional[str]:
    """Fetch advice from ZenQuotes API"""
    try:
        response = requests.get("https://zenquotes.io/api/random", timeout=2)
        response.raise_for_status()
        data = response.json()
        return f"{data[0]['q']} - {data[0]['a']}"
    except:
        return None


def rand_advice() -> Optional[str]:
    """
    Fetch random advice from various APIs with fallback options.
    Returns advice string or uses cache if APIs are slow.
    """
    global LAST_API_CALL, advice_cache

    # Local fallback advice
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

    # Try to get advice from APIs concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_api = {
            executor.submit(fetch_advice_slip): "AdviceSlip",
            executor.submit(fetch_zen_quotes): "ZenQuotes",
        }

        for future in as_completed(future_to_api, timeout=3):
            try:
                advice = future.result()
                if advice:
                    # Add to cache and update last call time
                    if len(advice_cache) >= CACHE_SIZE:
                        advice_cache.pop(0)
                    advice_cache.append(advice)
                    LAST_API_CALL = current_time
                    print(f"Successfully fetched advice from {future_to_api[future]}")
                    return advice
            except:
                continue

    # If all APIs fail, use local fallback
    print("All advice APIs failed, using local fallback")
    return random.choice(fallback_advice)


# Example usage
if __name__ == "__main__":
    advice = rand_advice()
    if advice:
        speak(advice)
    else:
        speak("Failed to get advice")
