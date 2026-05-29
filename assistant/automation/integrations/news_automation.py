import html
import requests
from dotenv import load_dotenv
import os
import time
import re
from assistant.core.speak_selector import speak, wait_for_tts_completion
from assistant.core.ear import listen

load_dotenv()

newsapi = os.getenv("NEWS_API_KEY")


def get_country_by_ip() -> str:
    """
    Dynamically detect the user's country code using their IP address.
    Falls back to 'in' if the lookup fails.
    """
    try:
        response = requests.get(f"https://ipinfo.io", timeout=10)
        if response.status_code == 200:
            data = response.json()
            country = data.get("country", "").lower()
            if country:
                return country
        
        # Fallback to geocoder
        import geocoder
        g = geocoder.ip("me")
        if g.ok and g.country:
            return g.country.lower()
            
        return "in"
    except Exception as e:
        print(f"Location lookup error: {e}")
        try:
            import geocoder
            g = geocoder.ip("me")
            if g.ok and g.country:
                return g.country.lower()
        except:
            pass
        return "in"  # Default to India if the lookup fails


def get_news_everything_endpoint(category: str = "general", limit: int = 3) -> None:
    """
    Fetches news using the /v2/everything endpoint, focused on the user's country.
    """
    if not newsapi:
        print("News API key is missing")
        speak("News service is not configured. Please check your API key.")
        return

    # Step 1: Get the dynamic country code
    dynamic_country = get_country_by_ip()

    # A mapping to help make the search query more natural
    category_query_map = {
        "general": "India",
        "sports": f"sports India",
        "technology": f"technology India",
        "health": f"health India",
        "business": f"business India",
        "entertainment": f"entertainment India",
        "science": f"science India",
    }

    # Use the category to create a search query focused on the detected country
    query = category_query_map.get(category, "India")

    # Step 2: Use the /v2/everything endpoint
    everything_url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": newsapi,
        "q": query,  # The dynamic search query
        "pageSize": limit,
        "sortBy": "publishedAt",  # Get the most recent articles
        "language": "en",
        # You can also use the 'sources' parameter to limit to specific Indian outlets
    }

    try:
        response = requests.get(everything_url, params=params, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        news_data = response.json()

        if news_data.get("status") == "ok":
            articles = news_data.get("articles", [])
            # Filter out removed or empty articles
            valid_articles = [
                a for a in articles if a.get("title") and a.get("title") != "[Removed]"
            ]

            if valid_articles:
                country_name = "India" if dynamic_country == "in" else "your region"
                speak(
                    f"Here are the top {len(valid_articles)} {category} headlines for {country_name}."
                )

                for idx, article in enumerate(valid_articles, start=1):
                    title = html.unescape(article.get("title", "No title"))
                    source = html.unescape(
                        article.get("source", {}).get("name", "Unknown source")
                    )
                    description = html.unescape(article.get("description", ""))

                    # "News anchor" style transitions
                    if idx == 1:
                        speak(f"Our top story today comes from {source}.")
                    else:
                        speak(f"In other news, {source} reports:")
                    
                    speak(title)
                    
                    if description:
                        # Clean HTML tags if any and truncate for brevity
                        clean_desc = re.sub(r'<[^>]+>', '', description)
                        if len(clean_desc) > 250:
                            clean_desc = clean_desc[:247] + "..."
                        speak(f"Here are the details. {clean_desc}")
                    
                    # Small pause for the user to digest the information
                    time.sleep(1.2)
                return
            else:
                print("No valid articles found in the response.")
        else:
            print(f"API response not OK: {news_data.get('message', 'Unknown error')}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Fallback message if everything fails
    print("Could not fetch any news articles.")
    speak(
        "Sorry, I couldn't fetch any news articles at the moment. Please try again later."
    )


# Update your tell_me_news function to use the new method
def tell_me_news() -> None:
    """Direct function for 'tell me news' command - fetches general news for the user's country"""
    speak("Fetching the top news headlines for your location.")
    get_news_everything_endpoint("general", limit=3)


# Keep your existing tell_news() function for category-based selection,
# but ensure it calls get_news_everything_endpoint instead of get_indian_news.


def tell_news() -> None:
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
    
    # Identify category by checking if keywords exist in the user's speech
    final_category = "general"
    for key, val in category_mapping.items():
        if key in category_raw:
            final_category = val
            break

    get_news_everything_endpoint(final_category, limit=3)


if __name__ == "__main__":
    tell_news()


# --- Command Handlers ---
from assistant.core.registry import on_fuzzy

@on_fuzzy(["tell me news", "what's the news", "today's news", "latest news", "news headlines", "top headlines", "current news"], score_cutoff=90)
def handle_news_cmd():
    tell_news()

