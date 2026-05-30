"""
LLM Tools Module

Provides functions that the LLM can natively call using Function Calling.
These functions wrap the existing automation scripts so the LLM can use them seamlessly.
"""

from typing import Optional, Dict, Any
from assistant.automation.integrations.check_weather import _fetch_weather_data, _extract_comprehensive_data, get_location
from assistant.automation.integrations.detailed_web_search import get_web_info
from assistant.core.logger import get_logger

logger = get_logger("LLMTools")

def get_weather(location: str = "current") -> str:
    """
    Get the current weather conditions for a specific location.
    
    Args:
        location: The city and country (e.g., 'London, UK'). Use 'current' for the user's current location.
    """
    logger.info(f"LLM called tool: get_weather(location={location})")
    try:
        if location.lower() == "current":
            loc_info = get_location()
            if not loc_info:
                return "Error: Could not determine current location."
            weather_data = _fetch_weather_data(lat=loc_info["latitude"], lon=loc_info["longitude"])
            city = loc_info["city"]
            country = loc_info["country"]
        else:
            weather_data = _fetch_weather_data(address=location)
            city = weather_data.get("name", location) if weather_data else location
            country = weather_data.get("sys", {}).get("country", "") if weather_data else ""
            
        if not weather_data:
            return f"Error: Could not fetch weather for {location}."
            
        data = _extract_comprehensive_data(weather_data, "metric", city, country)
        return str(data)
    except Exception as e:
        logger.error(f"Error in get_weather tool: {e}")
        return f"Error fetching weather: {str(e)}"

def search_web(query: str) -> str:
    """
    Search the internet for up-to-date information, news, or facts.
    Use this when the user asks a question about recent events or something outside your training data.
    
    Args:
        query: The search query to look up on the web.
    """
    logger.info(f"LLM called tool: search_web(query={query})")
    try:
        # get_web_info returns a summarized string of the search results
        result = get_web_info(query, max_results=3, prints=False)
        return result
    except Exception as e:
        logger.error(f"Error in search_web tool: {e}")
        return f"Error searching the web: {str(e)}"

# List of tools to pass to the LLM
AVAILABLE_TOOLS = [get_weather, search_web]
