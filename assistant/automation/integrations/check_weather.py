import requests
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

load_dotenv()


def get_location():
    """Helper function to get current location from IP address"""
    try:
        location_response = requests.get("https://ipapi.co/json/", timeout=5)
        location_data = location_response.json()

        lat = location_data.get("latitude")
        lon = location_data.get("longitude")
        city = location_data.get("city", "your location")
        country = location_data.get("country_name", "")

        if lat is None or lon is None:
            print("Could not determine location from IP address")
            return None

        return {"latitude": lat, "longitude": lon, "city": city, "country": country}
    except requests.exceptions.RequestException as e:
        print(f"Error getting location: {str(e)}")
        return None


def get_current_temperature(units="metric"):
    """Get current temperature information for your location"""
    try:
        WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
        if not WEATHER_API_KEY:
            print(
                "OpenWeatherMap API key is required. Please set the WEATHER_API_KEY environment variable."
            )
            return

        location_info = get_location()
        if not location_info:
            return

        url = f"https://api.openweathermap.org/data/2.5/weather?lat={location_info['latitude']}&lon={location_info['longitude']}&appid={WEATHER_API_KEY}"

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
            return

        if "main" not in weather_data or "weather" not in weather_data:
            print("Invalid response from weather API")
            speak(
                "Sorry, I couldn't get the temperature right now. Please try again after some time"
            )
            return

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
            f"Current temperature in {location_info['city']}, {location_info['country']} is {temp}{unit_symbol}. "
            f"Low: {min_temp}{unit_symbol} and High: {max_temp}{unit_symbol}."
        )

    except requests.exceptions.RequestException as e:
        print(f"Network error: Please check your internet connection. {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


def get_overall_weather(units="metric"):
    """Get comprehensive weather information for your location"""
    try:
        WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
        if not WEATHER_API_KEY:
            print(
                "OpenWeatherMap API key is required. Please set the WEATHER_API_KEY environment variable."
            )
            return

        location_info = get_location()
        if not location_info:
            return

        url = f"https://api.openweathermap.org/data/2.5/weather?lat={location_info['latitude']}&lon={location_info['longitude']}&appid={WEATHER_API_KEY}"

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
            return

        if "main" not in weather_data or "weather" not in weather_data:
            print("Invalid response from weather API")
            speak(
                "Sorry, I couldn't get the weather information right now. Please try again after some time"
            )
            return

        # Extract comprehensive weather data
        main_data = weather_data["main"]
        weather_desc = weather_data["weather"][0]
        wind_data = weather_data.get("wind", {})
        visibility = weather_data.get("visibility", 0) / 1000
        clouds = weather_data.get("clouds", {}).get("all", 0)

        temp = main_data["temp"]
        feels_like = main_data["feels_like"]
        humidity = main_data["humidity"]
        pressure = main_data["pressure"]

        weather_main = weather_desc["main"]
        weather_description = weather_desc["description"].title()

        wind_speed = wind_data.get("speed", 0)
        wind_deg = wind_data.get("deg", 0)

        # Determine wind direction
        def get_wind_direction(degrees):
            directions = [
                "North",
                "Northeast",
                "East",
                "Southeast",
                "South",
                "Southwest",
                "West",
                "Northwest",
            ]
            idx = int((degrees + 22.5) / 45) % 8
            return directions[idx]

        wind_direction = get_wind_direction(wind_deg) if wind_deg else "Unknown"

        # Set unit symbols
        if units == "metric":
            temp_unit = "°C"
            speed_unit = "m/s"
        elif units == "imperial":
            temp_unit = "°F"
            speed_unit = "mph"
        else:
            temp_unit = "K"
            speed_unit = "m/s"

        # Create comprehensive weather report
        weather_report = (
            f"Weather report for {location_info['city']}, {location_info['country']}: "
            f"It's currently {weather_description} with a temperature of {temp}{temp_unit}, "
            f"feels like {feels_like}{temp_unit}. "
            f"Humidity is {humidity}%, atmospheric pressure is {pressure} hPa. "
        )

        if wind_speed > 0:
            weather_report += f"Wind is blowing from the {wind_direction} at {wind_speed} {speed_unit}. "

        if clouds > 0:
            weather_report += f"Cloud cover is {clouds}%. "

        if visibility > 0:
            weather_report += f"Visibility is {visibility:.1f} kilometers."

        speak(weather_report)

        # Also return the data for potential use by other functions
        return {
            "location": location_info,
            "temperature": temp,
            "feels_like": feels_like,
            "weather": weather_main,
            "description": weather_description,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "clouds": clouds,
            "visibility": visibility,
            "units": units,
        }

    except requests.exceptions.RequestException as e:
        print(f"Network error: Please check your internet connection. {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


def get_weather_by_address(address: str, units: str = "metric"):
    """
    Get comprehensive weather information for a given address/city name.

    address: city name, or "city,state,country" (ISO 3166 country code recommended).
    units: "metric", "imperial", or leave default for Kelvin (no units param).

    Returns a dict similar to get_overall_weather and uses speak(...) to announce the report.
    """
    try:
        if not address or not isinstance(address, str):
            print("Please provide a valid address/city name as a string.")
            return

        WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
        if not WEATHER_API_KEY:
            print(
                "OpenWeatherMap API key is required. Please set the WEATHER_API_KEY environment variable."
            )
            return

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": address, "appid": WEATHER_API_KEY}

        if units == "metric":
            params["units"] = "metric"
        elif units == "imperial":
            params["units"] = "imperial"

        response = requests.get(url, params=params, timeout=10)
        weather_data = response.json()

        if response.status_code != 200:
            # Common case: city not found -> 404, message in JSON
            print(
                f"Error from weather API: {weather_data.get('message', 'Unknown error')}"
            )
            return

        if "main" not in weather_data or "weather" not in weather_data:
            print("Invalid response from weather API")
            speak(
                "Sorry, I couldn't get the weather information for that place right now."
            )
            return

        # Extract comprehensive weather data
        main_data = weather_data["main"]
        weather_desc = weather_data["weather"][0]
        wind_data = weather_data.get("wind", {})
        visibility = weather_data.get("visibility", 0) / 1000
        clouds = weather_data.get("clouds", {}).get("all", 0)

        temp = main_data["temp"]
        feels_like = main_data.get("feels_like")
        humidity = main_data.get("humidity")
        pressure = main_data.get("pressure")

        weather_main = weather_desc.get("main", "")
        weather_description = weather_desc.get("description", "").title()

        wind_speed = wind_data.get("speed", 0)
        wind_deg = wind_data.get("deg", 0)

        # Determine wind direction (same helper as get_overall_weather)
        def get_wind_direction(degrees):
            directions = [
                "North",
                "Northeast",
                "East",
                "Southeast",
                "South",
                "Southwest",
                "West",
                "Northwest",
            ]
            idx = int((degrees + 22.5) / 45) % 8
            return directions[idx]

        wind_direction = get_wind_direction(wind_deg) if wind_deg else "Unknown"

        # Set unit symbols
        if units == "metric":
            temp_unit = "°C"
            speed_unit = "m/s"
        elif units == "imperial":
            temp_unit = "°F"
            speed_unit = "mph"
        else:
            temp_unit = "K"
            speed_unit = "m/s"

        # City and country returned by API
        city_name = weather_data.get("name", address)
        sys_data = weather_data.get("sys", {})
        country_name = sys_data.get("country", "")

        # Create comprehensive weather report
        weather_report = (
            f"Weather report for {city_name}, {country_name}: "
            f"It's currently {weather_description} with a temperature of {temp}{temp_unit}, "
            f"feels like {feels_like}{temp_unit}. "
            f"Humidity is {humidity}%, atmospheric pressure is {pressure} hPa. "
        )

        if wind_speed > 0:
            weather_report += f"Wind is blowing from the {wind_direction} at {wind_speed} {speed_unit}. "

        if clouds > 0:
            weather_report += f"Cloud cover is {clouds}%. "

        if visibility > 0:
            weather_report += f"Visibility is {visibility:.1f} kilometers."

        speak(weather_report)

        # Return structured data like get_overall_weather
        return {
            "location": {"city": city_name, "country": country_name},
            "temperature": temp,
            "feels_like": feels_like,
            "weather": weather_main,
            "description": weather_description,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "clouds": clouds,
            "visibility": visibility,
            "units": units,
        }

    except requests.exceptions.RequestException as e:
        print(f"Network error: Please check your internet connection. {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    # Option 1: Just temperature
    # get_current_temperature(units="metric")

    # Option 2: Comprehensive weather information
    get_overall_weather(units="metric")

    # Option 3: Get weather by address
    # get_weather_by_address("Bangalore")
