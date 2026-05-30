"""
Module for retrieving and announcing network-related information, 
including geographic location and public IP address.
"""

import time
import requests
from assistant.core.speak_selector import speak
import geocoder


def get_current_location() -> None:
    """
    Determines and announces the user's approximate geographic location via IP.
    """
    try:
        g = geocoder.ip("me")

        if g.ok:
            city = g.city
            state = g.state
            country = g.country
            speak(
                f"Based on your IP address, you appear to be in {city}, {state}, {country}"
            )
        else:
            speak("Sorry, I couldn't determine your current location")
    except Exception as e:
        print(f"Error getting location: {e}")
        speak("Sorry, I'm having trouble determining your location")


def check_ip_address() -> bool:
    """
    Fetches the user's public IP address from a remote service with retry logic.
    """
    max_attempts = 3
    timeout_duration = 5
    retry_delay = 2

    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                speak(f"Attempt {attempt + 1} to fetch your IP address.")

            response = requests.get("https://api.ipify.org", timeout=timeout_duration)
            response.raise_for_status()

            speak(f"Your IP address is {response.text}")
            return True
        except requests.exceptions.Timeout:
            print(f"Timeout occurred on attempt {attempt+1}")
            if attempt < max_attempts - 1:
                time.sleep(retry_delay)
                continue
            else:
                speak("Request timed out. Please check your internet connection.")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error on attempt {attempt+1}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(retry_delay)
                continue
            else:
                speak("Failed to retrieve IP address due to a server error.")
        except requests.exceptions.RequestException as e:
            print(f"Network error on attempt {attempt+1}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(retry_delay)
                continue
            else:
                speak(
                    "Unable to fetch the IP address after several attempts. Please check your internet connection."
                )

    return False


from assistant.core.registry import on_fuzzy

@on_fuzzy(["current location", "where am i", "my location", "where am I right now"], score_cutoff=90)
def handle_location():
    """Handles voice commands to identify the user's location."""
    get_current_location()

@on_fuzzy(["check ip address", "check my ip address", "what is my ip"], score_cutoff=90)
def handle_ip_check():
    """Handles voice commands to identify the user's public IP."""
    check_ip_address()
