"""
Module for fetching and narrating localized news headlines using the NewsAPI.
"""

import html
import requests
import time
import re
from assistant.core.config import config
from assistant.core.speak_selector import speak, wait_for_tts_completion
from assistant.core.ear import listen
from assistant.core.mouth import tts_queue
import uuid

newsapi = config.news_api_key


def get_country_by_ip() -> str:
    """
    Detects the user's country code via IP geolocation services.
    """
    # 1. Try ip-api.com
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                country = data.get("countryCode", "").lower()
                if country:
                    return country
    except Exception as e:
        print(f"Location lookup (ip-api.com) failed: {e}")

    # 2. Try ipapi.co
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            country = data.get("country", "").lower()
            if country:
                return country
    except Exception as e:
        print(f"Location lookup (ipapi.co) failed: {e}")

    # 3. Try ipinfo.io
    try:
        response = requests.get("https://ipinfo.io", timeout=10)
        if response.status_code == 200:
            data = response.json()
            country = data.get("country", "").lower()
            if country:
                return country
    except Exception as e:
        print(f"Location lookup (ipinfo.io) failed: {e}")

    # 4. Fallback to geocoder
    try:
        import geocoder
        g = geocoder.ip("me")
        if g.ok and g.country:
            return g.country.lower()
    except Exception as e:
        print(f"Location lookup (geocoder) failed: {e}")

    return "in"  # Default to India if all lookups fail


def get_news_everything_endpoint(category: str = "general", limit: int = 3) -> None:
    """
    Retrieves and speaks news articles based on a category and user location.
    """
    if not newsapi:
        print("News API key is missing")
        speak("News service is not configured. Please check your API key.")
        return

    dynamic_country = get_country_by_ip()

    category_query_map = {
        "general": "India",
        "sports": "sports India",
        "technology": "technology India",
        "health": "health India",
        "business": "business India",
        "entertainment": "entertainment India",
        "science": "science India",
    }

    query = category_query_map.get(category, "India")

    everything_url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": newsapi,
        "q": query,
        "pageSize": limit,
        "sortBy": "publishedAt",
        "language": "en",
    }

    try:
        response = requests.get(everything_url, params=params, timeout=10)
        response.raise_for_status()
        news_data = response.json()

        if news_data.get("status") == "ok":
            articles = news_data.get("articles", [])
            valid_articles = [
                a for a in articles if a.get("title") and a.get("title") != "[Removed]"
            ]

            if valid_articles:
                country_name = "India" if dynamic_country == "in" else "your region"
                news_message_id = str(uuid.uuid4())
                
                tts_queue.put((f"Here are the top {len(valid_articles)} {category} headlines for {country_name}.", None, news_message_id))

                for idx, article in enumerate(valid_articles, start=1):
                    title = html.unescape(article.get("title", "No title"))
                    source = html.unescape(
                        article.get("source", {}).get("name", "Unknown source")
                    )
                    description = html.unescape(article.get("description", ""))

                    if idx == 1:
                        tts_queue.put((f"Our top story today comes from {source}.", None, news_message_id))
                    else:
                        tts_queue.put((f"In other news, {source} reports:", None, news_message_id))
                    
                    tts_queue.put((title, None, news_message_id))
                    
                    if description:
                        clean_desc = re.sub(r'<[^>]+>', '', description)
                        if len(clean_desc) > 250:
                            clean_desc = clean_desc[:247] + "..."
                        tts_queue.put((f"Here are the details. {clean_desc}", None, news_message_id))
                    
                    time.sleep(0.1) # Small delay to queue them up properly
                return
            else:
                print("No valid articles found in the response.")
        else:
            print(f"API response not OK: {news_data.get('message', 'Unknown error')}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("Could not fetch any news articles.")
    speak(
        "Sorry, I couldn't fetch any news articles at the moment. Please try again later."
    )


def tell_me_news() -> None:
    """
    Triggers a general news update for the user's location.
    """
    speak("Fetching the top news headlines for your location.")
    get_news_everything_endpoint("general", limit=3)


def tell_news() -> None:
    """
    Prompts the user for a news category and fetches relevant headlines.
    """
    speak(
        "Which category would you like? General, Sports, Technology, Health, Business, Entertainment, or Science?"
    )
    wait_for_tts_completion()
    category = listen()

    if category is None:
        speak("I didn't hear your response. Using general news.")
        category = "general"

    category_mapping = {
        "general": "general",
        "sports": "sports",
        "technology": "technology",
        "tech": "technology",
        "health": "health",
        "business": "business",
        "entertainment": "entertainment",
        "science": "science",
    }

    category_raw = category.lower().strip()
    
    final_category = "general"
    for key, val in category_mapping.items():
        if key in category_raw:
            final_category = val
            break

    get_news_everything_endpoint(final_category, limit=3)


if __name__ == "__main__":
    tell_news()


from assistant.core.registry import on_regex

@on_regex(r"^(tell me news|what's the news|today's news|latest news|news headlines|top headlines|current news)$", priority=2)
def handle_news_cmd():
    """
    Handles voice commands related to news requests.
    """
    tell_news()
