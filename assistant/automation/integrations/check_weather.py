import requests
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

# Load environment variables from .env file for secure API key storage
load_dotenv()


def get_location():
    """
    Determine current geographical location using IP address geolocation.

    Uses the ipapi.co service to get approximate location based on the
    device's public IP address. This provides automatic location detection
    without requiring manual input from the user.

    Returns:
        dict or None: Dictionary containing location information with keys:
            - latitude (float): Geographic latitude coordinate
            - longitude (float): Geographic longitude coordinate
            - city (str): City name based on IP geolocation
            - country (str): Country name based on IP geolocation
        Returns None if location cannot be determined or network error occurs.

    Example:
        >>> get_location()
        {'latitude': 40.7128, 'longitude': -74.0060, 'city': 'New York', 'country': 'United States'}

    Note:
        IP-based location may not be precise and can vary based on ISP
        and network configuration. Accuracy is typically at city level.
    """
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
    """
    Get and announce current temperature for the user's location.

    Fetches current weather data from OpenWeatherMap API and provides
    a voice report of the current temperature along with daily high/low.

    Args:
        units (str): Temperature unit system. Options:
                   "metric" - Celsius (default)
                   "imperial" - Fahrenheit
                   "standard" - Kelvin

    Process:
        1. Retrieves API key from environment variables
        2. Determines current location via IP geolocation
        3. Fetches weather data from OpenWeatherMap API
        4. Extracts temperature information
        5. Provides voice report to user

    Example Output:
        "Current temperature in New York, United States is 22°C. Low: 18°C and High: 26°C."

    Note:
        Requires WEATHER_API_KEY environment variable to be set with a valid
        OpenWeatherMap API key.
    """
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
    """
    Get comprehensive weather report for current location.

    Provides a detailed weather analysis including temperature, feels-like temperature,
    humidity, pressure, wind conditions, cloud cover, and visibility.

    Args:
        units (str): Measurement unit system. Options:
                   "metric" - Celsius, m/s (default)
                   "imperial" - Fahrenheit, mph
                   "standard" - Kelvin, m/s

    Returns:
        dict or None: Comprehensive weather data dictionary with keys:
            - location: Dictionary with city and country
            - temperature: Current temperature
            - feels_like: Apparent temperature
            - weather: Main weather condition (e.g., "Clear", "Rain")
            - description: Detailed weather description
            - humidity: Relative humidity percentage
            - pressure: Atmospheric pressure in hPa
            - wind_speed: Wind speed in selected units
            - wind_direction: Cardinal wind direction
            - clouds: Cloud coverage percentage
            - visibility: Visibility distance in kilometers
            - units: Unit system used for measurements

    Example Output:
        "Weather report for New York, United States: It's currently Clear Sky with a
         temperature of 22°C, feels like 24°C. Humidity is 65%, atmospheric pressure
         is 1013 hPa. Wind is blowing from the Northeast at 3.5 m/s. Cloud cover is
         10%. Visibility is 10.0 kilometers."

    Note:
        Wind direction is calculated from degrees to cardinal directions using
        8-point compass rose (N, NE, E, SE, S, SW, W, NW).
    """
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
        visibility = weather_data.get("visibility", 0) / 1000  # Convert meters to km
        clouds = weather_data.get("clouds", {}).get("all", 0)

        temp = main_data["temp"]
        feels_like = main_data["feels_like"]
        humidity = main_data["humidity"]
        pressure = main_data["pressure"]

        weather_main = weather_desc["main"]
        weather_description = weather_desc["description"].title()

        wind_speed = wind_data.get("speed", 0)
        wind_deg = wind_data.get("deg", 0)

        # Determine wind direction from degrees
        def get_wind_direction(degrees):
            """
            Convert wind direction in degrees to cardinal direction.

            Args:
                degrees (float): Wind direction in degrees (0-360)

            Returns:
                str: Cardinal direction (N, NE, E, SE, S, SW, W, NW)
            """
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

        # Set unit symbols based on measurement system
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
    Get comprehensive weather information for a specific location by address.

    Allows users to query weather for any city or location worldwide by providing
    an address string. Supports city names, city+country combinations, and other
    location formats recognized by OpenWeatherMap.

    Args:
        address (str): Location description. Can be:
                     - City name (e.g., "London")
                     - City,country code (e.g., "London,UK")
                     - City,state,country (e.g., "New York,NY,US")
        units (str): Measurement unit system. Same options as get_overall_weather.

    Returns:
        dict or None: Same comprehensive weather data structure as get_overall_weather,
                     but for the specified address location.

    Example:
        >>> get_weather_by_address("Paris,FR", "metric")
        # Provides weather report for Paris, France in Celsius

    Note:
        For best results, include country code with city names to avoid ambiguity
        between cities with the same name in different countries.
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
    """
    Demonstration and testing entry point for weather functions.

    When run as a standalone script, this demonstrates different ways to use
    the weather checking capabilities. Uncomment the desired function call.
    """
    # Option 1: Just temperature for current location
    # get_current_temperature(units="metric")

    # Option 2: Comprehensive weather information for current location
    get_overall_weather(units="metric")

    # Option 3: Get weather for specific address/location
    # get_weather_by_address("Bangalore")
