import time
import requests
from head.speak_selector import speak
import geocoder


def get_current_location():
    """Get the current location using IP geolocation"""
    try:
        # Get location based on IP address
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


def check_ip_address():
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
