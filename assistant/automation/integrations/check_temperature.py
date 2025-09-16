import requests
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

load_dotenv()


def get_current_temperature(units="metric"):
    try:
        WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

        if not WEATHER_API_KEY:
            print(
                "OpenWeatherMap API key is required. Please set the WEATHER_API_KEY environment variable."
            )

        location_response = requests.get("https://ipapi.co/json/", timeout=5)
        location_data = location_response.json()
        lat = location_data.get("latitude")
        lon = location_data.get("longitude")
        city = location_data.get("city", "your location")
        country = location_data.get("country_name", "")

        if lat is None or lon is None:
            print("Could not determine location from IP address")

        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}"

        if units == "metric":
            url += "&units=metric"
        elif units == "imperial":
            url += "&units=imperial"

        response = requests.get(url, timeout=10)
        weather_data = response.json()

        if response.status_code != 200:
            print(
                f"Error from weather API: {weather_data.get('message', 'Unknown error')}"
            )

        if "main" not in weather_data or "weather" not in weather_data:
            print("Invalid response from weather API")
            speak(
                "Sorry, I couldn't get the temperature right now. Please try again after some time"
            )

        main_data = weather_data["main"]

        temp = main_data["temp"]
        min_temp = main_data["temp_min"]
        max_temp = main_data["temp_max"]

        if units == "metric":
            unit_symbol = "°C"
        elif units == "imperial":
            unit_symbol = "°F"
        else:
            unit_symbol = "K"

        speak(
            f"Current temperature in {city}, {country} is {temp}{unit_symbol}. "
            f"Low: {min_temp}{unit_symbol} and High: {max_temp}{unit_symbol}. "
        )

    except requests.exceptions.RequestException as e:
        print(f"Network error: Please check your internet connection. {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    speak(get_current_temperature(units="metric"))
