"""
Module for retrieving and announcing weather information using OpenWeatherMap API.
Provides functionality for location detection, temperature checks, and detailed reports.
"""

import requests
import os
import geocoder
from dotenv import load_dotenv
from assistant.core.speak_selector import speak
from typing import Dict, Union, Optional, Any

load_dotenv()

def get_location() -> Optional[Dict[str, Union[float, str]]]:
    """
    Detects the user's current geographical location via IP geolocation services.
    """
    try:
        location_response = requests.get("https://ipapi.co/json/", timeout=5)
        if location_response.status_code == 200:
            location_data = location_response.json()
            lat = location_data.get("latitude")
            lon = location_data.get("longitude")
            city = location_data.get("city", "your location")
            country = location_data.get("country_name", "")
            
            if lat is not None and lon is not None:
                return {"latitude": lat, "longitude": lon, "city": city, "country": country}

        g = geocoder.ip("me")
        if g.ok:
            return {
                "latitude": g.latlng[0],
                "longitude": g.latlng[1],
                "city": g.city if g.city else "your location",
                "country": g.country if g.country else ""
            }
        
        print("Could not determine location from any service")
        return None
    except Exception as e:
        print(f"Error getting location: {str(e)}")
        try:
            g = geocoder.ip("me")
            if g.ok:
                return {
                    "latitude": g.latlng[0],
                    "longitude": g.latlng[1],
                    "city": g.city if g.city else "your location",
                    "country": g.country if g.country else ""
                }
        except:
            pass
        return None

def get_wind_direction(degrees: float) -> str:
    """
    Maps wind direction in degrees to a cardinal direction string.
    """
    directions = [
        "North", "Northeast", "East", "Southeast",
        "South", "Southwest", "West", "Northwest",
    ]
    idx = int((degrees + 22.5) / 45) % 8
    return directions[idx]

def _fetch_weather_data(lat: Optional[float] = None, lon: Optional[float] = None, address: Optional[str] = None, units: str = "metric") -> Optional[Dict[str, Any]]:
    """
    Internal helper to query the OpenWeatherMap API for weather data.
    """
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    if not WEATHER_API_KEY:
        print("OpenWeatherMap API key is required. Please set the WEATHER_API_KEY environment variable.")
        return None
        
    if address:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": address, "appid": WEATHER_API_KEY}
    elif lat is not None and lon is not None:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "appid": WEATHER_API_KEY}
    else:
        return None
        
    if units in ["metric", "imperial"]:
        params["units"] = units
        
    response = requests.get(url, params=params, timeout=10)
    weather_data = response.json()
    
    if response.status_code != 200:
        print(f"Error from weather API: {weather_data.get('message', 'Unknown error')}")
        return None
        
    if "main" not in weather_data or "weather" not in weather_data:
        print("Invalid response from weather API")
        return None
        
    return weather_data

def _format_weather_report(weather_data: Dict[str, Any], units: str, city_name: str, country_name: str) -> str:
    """
    Internal helper to generate a human-readable weather report string.
    """
    main_data = weather_data["main"]
    weather_desc = weather_data["weather"][0]
    wind_data = weather_data.get("wind", {})
    visibility = weather_data.get("visibility", 0) / 1000
    clouds = weather_data.get("clouds", {}).get("all", 0)

    temp = main_data["temp"]
    feels_like = main_data.get("feels_like", temp)
    humidity = main_data.get("humidity", 0)
    pressure = main_data.get("pressure", 0)
    weather_description = weather_desc.get("description", "").title()
    wind_speed = wind_data.get("speed", 0)
    wind_deg = wind_data.get("deg", 0)

    wind_direction = get_wind_direction(wind_deg) if wind_deg else "Unknown"

    if units == "metric":
        temp_unit = "°C"
        speed_unit = "m/s"
    elif units == "imperial":
        temp_unit = "°F"
        speed_unit = "mph"
    else:
        temp_unit = "K"
        speed_unit = "m/s"

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

    return weather_report

def _extract_comprehensive_data(weather_data: Dict[str, Any], units: str, city_name: str, country_name: str) -> Dict[str, Any]:
    """
    Internal helper to parse raw API data into a structured dictionary.
    """
    main_data = weather_data["main"]
    wind_data = weather_data.get("wind", {})
    wind_deg = wind_data.get("deg", 0)
    
    return {
        "location": {"city": city_name, "country": country_name},
        "temperature": main_data["temp"],
        "feels_like": main_data.get("feels_like"),
        "weather": weather_data["weather"][0].get("main", ""),
        "description": weather_data["weather"][0].get("description", "").title(),
        "humidity": main_data.get("humidity"),
        "pressure": main_data.get("pressure"),
        "wind_speed": wind_data.get("speed", 0),
        "wind_direction": get_wind_direction(wind_deg) if wind_deg else "Unknown",
        "clouds": weather_data.get("clouds", {}).get("all", 0),
        "visibility": weather_data.get("visibility", 0) / 1000,
        "units": units,
    }


def get_current_temperature(units: str = "metric") -> None:
    """
    Fetches and speaks the current temperature for the user's location.
    """
    try:
        location_info = get_location()
        if not location_info:
            return

        weather_data = _fetch_weather_data(lat=location_info["latitude"], lon=location_info["longitude"], units=units)
        
        if not weather_data:
            speak("Sorry, I couldn't get the temperature right now. Please try again after some time")
            return

        main_data = weather_data["main"]
        temp = main_data["temp"]
        min_temp = main_data["temp_min"]
        max_temp = main_data["temp_max"]

        unit_symbol = "°C" if units == "metric" else "°F" if units == "imperial" else "K"

        speak(
            f"Current temperature in {location_info['city']}, {location_info['country']} is {temp}{unit_symbol}. "
            f"Low: {min_temp}{unit_symbol} and High: {max_temp}{unit_symbol}."
        )

    except requests.exceptions.RequestException as e:
        print(f"Network error: {str(e)}")
        speak("I'm having trouble connecting to the weather service. Please check your internet connection.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        speak("Sorry, I encountered an unexpected error while checking the weather.")


def get_overall_weather(units: str = "metric") -> Optional[Dict[str, Any]]:
    """
    Fetches and speaks a comprehensive weather report for the user's location.
    """
    try:
        location_info = get_location()
        if not location_info:
            return None

        weather_data = _fetch_weather_data(lat=location_info["latitude"], lon=location_info["longitude"], units=units)
        
        if not weather_data:
            speak("Sorry, I couldn't get the weather information right now. Please try again after some time")
            return None

        report_str = _format_weather_report(weather_data, units, location_info["city"], location_info["country"])
        speak(report_str)

        return _extract_comprehensive_data(weather_data, units, location_info["city"], location_info["country"])

    except requests.exceptions.RequestException as e:
        print(f"Network error: {str(e)}")
        speak("I couldn't reach the weather server. Please check your internet connection.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        speak("I encountered a problem while fetching the weather report.")


def get_weather_by_address(address: str, units: str = "metric") -> Optional[Dict[str, Any]]:
    """
    Fetches and speaks weather information for a specific location string.
    """
    try:
        if not address or not isinstance(address, str):
            print("Please provide a valid address/city name as a string.")
            return None

        weather_data = _fetch_weather_data(address=address, units=units)
        
        if not weather_data:
            speak("Sorry, I couldn't get the weather information for that place right now.")
            return None

        city_name = weather_data.get("name", address)
        country_name = weather_data.get("sys", {}).get("country", "")

        report_str = _format_weather_report(weather_data, units, city_name, country_name)
        speak(report_str)

        return _extract_comprehensive_data(weather_data, units, city_name, country_name)

    except requests.exceptions.RequestException as e:
        print(f"Network error: {str(e)}")
        speak(f"I'm sorry, I couldn't get the weather for {address} due to a network issue.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        speak(f"I had trouble fetching the weather information for {address}.")


if __name__ == "__main__":
    get_overall_weather(units="metric")


from assistant.core.registry import on_regex, on_fuzzy

@on_fuzzy(["check temperature", "check the temperature", "what is the temperature"], score_cutoff=90)
def handle_temp():
    """Handles voice commands to check current temperature."""
    speak("Checking the temperature. Please wait a moment...")
    get_current_temperature()

@on_regex(r"(?:check\s+(?:the\s+)?)?weather$")
@on_fuzzy(["what's the weather today", "check today's weather", "today's weather", "weather today", "check the weather"], score_cutoff=90)
def handle_weather_today():
    """Handles voice commands to check today's weather."""
    speak("Checking Today's weather conditions. Please wait a moment...")
    get_overall_weather()

@on_regex(r"(?:check\s+the\s+)?weather\s+(?:in|for|at|of)\s+(?P<location>.*)$")
def handle_weather_location(location):
    """Handles voice commands to check weather in a specific location."""
    speak(f"Checking the weather in {location}. Please wait a moment...")
    get_weather_by_address(address=location)
