import time
import requests
from assistant.core.speak_selector import speak
import geocoder


def get_current_location():
    """
    Determine and announce the user's current geographic location using IP geolocation.

    This function uses the geocoder library to approximate the user's location
    based on their public IP address. The geolocation data includes city, state,
    and country information derived from the IP address's geographic mapping.

    Process:
        1. Queries the geocoder IP service with the current machine's public IP
        2. Extracts city, state, and country information from the response
        3. Provides voice feedback with the determined location
        4. Handles errors gracefully with user-friendly messages

    Accuracy Note:
        IP-based geolocation provides approximate location at the city level.
        Accuracy varies by ISP and network configuration. For precise location,
        GPS or user-provided location data would be required.

    Example Output:
        "Based on your IP address, you appear to be in New York, NY, United States"

    Raises:
        Exception: Catches and handles any errors during the geolocation process,
                  providing voice feedback rather than crashing the application.
    """
    try:
        # Get location based on IP address using geocoder's automatic IP detection
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
    """
    Retrieve and announce the user's public IP address with robust error handling.

    This function makes multiple attempts to fetch the public IP address from
    the ipify.org API service. It includes comprehensive error handling for
    network issues, timeouts, and server errors with automatic retry logic.

    Features:
        - Multiple retry attempts (3 total attempts)
        - Configurable timeouts and retry delays
        - Progressive voice feedback during retries
        - Comprehensive error classification and handling

    Process:
        1. Attempts to fetch IP from https://api.ipify.org
        2. Implements exponential backoff with 2-second delays between retries
        3. Provides specific error messages for different failure types
        4. Announces successful IP retrieval via voice

    Returns:
        bool: True if IP address was successfully retrieved and announced,
              False if all attempts failed.

    Example Output:
        "Your IP address is 192.168.1.100"

    Error Handling:
        - Timeout: Retries with increasing delays, informs user about connection issues
        - HTTP Errors: Retries for server-side issues, provides specific error context
        - Network Errors: Retries for general connectivity problems
        - All Failures: Provides comprehensive failure message after final attempt
    """
    max_attempts = 3
    timeout_duration = 5
    retry_delay = 2

    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                speak(f"Attempt {attempt + 1} to fetch your IP address.")

            # Use ipify.org service which returns plain text IP address
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
