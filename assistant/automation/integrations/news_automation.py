import html
import requests
from dotenv import load_dotenv
import os
import time
from assistant.core.speak_selector import speak
from assistant.core.ear import listen

load_dotenv()

newsapi = os.getenv("NEWS_API_KEY")


def get_country_by_ip():
    """
    Dynamically detect the user's country code using their IP address.
    Falls back to 'in' if the lookup fails.
    """
    try:
        response = requests.get(f"https://ipinfo.io", timeout=10)
        data = response.json()
        country = data.get("country", "in").lower()
        return country
    except Exception as e:
        return "in"  # Default to India if the lookup fails


def get_news_everything_endpoint(category="general", limit=3):
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

                    speak(f"Story {idx}: {title}")
                    time.sleep(1)  # Pause between headlines
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
def tell_me_news():
    """Direct function for 'tell me news' command - fetches general news for the user's country"""
    speak("Fetching the top news headlines for your location.")
    get_news_everything_endpoint("general", limit=3)


# Keep your existing tell_news() function for category-based selection,
# but ensure it calls get_news_everything_endpoint instead of get_indian_news.


def tell_news():
    speak(
        "Which category would you like? General, Sports, Technology, Health, Business, Entertainment, or Science?"
    )
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

    category = category.lower().strip()
    category = category_mapping.get(category, "general")

    get_news_everything_endpoint(category, limit=3)


if __name__ == "__main__":
    tell_news()
