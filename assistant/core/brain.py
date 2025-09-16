import wikipedia
import threading
import sys
import time
import webbrowser
import os
import json
import logging
import tempfile
from pathlib import Path
from urllib.parse import quote
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "brain_function.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

try:
    from assistant.core.speak_selector import speak
    from assistant.nlp.model import mind
    from assistant.activities.activity_monitor import record_user_activity
except ImportError as e:
    logger.error(f"Import error: {e}")
    speak = print
    mind = lambda text, threshold=0.7: "I'm having trouble accessing my knowledge base."
    record_user_activity = lambda: None

try:
    from fuzzywuzzy import fuzz, process

    FUZZY_MATCHING_AVAILABLE = True
    logger.info("Fuzzywuzzy imported successfully for partial matching")
except ImportError:
    FUZZY_MATCHING_AVAILABLE = False
    logger.warning("Fuzzywuzzy not available, using basic partial matching")

qa_lock = threading.Lock()

# Cache for Wikipedia results to avoid repeated API calls
wiki_cache = {}
CACHE_EXPIRY_HOURS = 24


def load_qa_data(file_path):
    """Load Q&A data from JSON file for better structure"""
    file_path = Path(file_path)
    qa_dict = {}

    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert list format to dictionary if needed for backward compatibility
                if isinstance(data, list):
                    for item in data:
                        if ":" in item:
                            q, a = item.split(":", 1)
                            qa_dict[q.strip()] = a.strip()
                else:
                    qa_dict = data
        logger.info(f"Loaded {len(qa_dict)} Q&A pairs from {file_path}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load QA data: {e}, starting with empty dataset")
    except Exception as e:
        logger.error(f"Unexpected error loading QA data: {e}")

    return qa_dict


def save_qa_data(file_path, qa_dict):
    """Save Q&A data to JSON file using atomic writing with temporary files"""
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a temporary file in the same directory for atomic writing
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(file_path.parent),
            delete=False,
            suffix=".tmp",
        ) as tmp_file:
            json.dump(qa_dict, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = tmp_file.name

        # Replace the original file with the temporary file atomically
        if os.path.exists(file_path):
            os.replace(tmp_path, str(file_path))
        else:
            os.rename(tmp_path, str(file_path))

        logger.info(f"Saved {len(qa_dict)} Q&A pairs to {file_path}")
    except Exception as e:
        logger.error(f"Error saving QA data: {e}")
        # Clean up temporary file if something went wrong
        try:
            os.unlink(tmp_path)
        except:
            pass


# Use JSON format for better data structure
qa_file_path = (
    r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\brain_data\qna_data.json"
)
qa_dict = load_qa_data(qa_file_path)


def find_best_match(query, qa_dict, threshold=70):
    """Find the best matching question in the Q&A database using partial matching"""
    if not qa_dict:
        return None

    # Try fuzzy matching if available
    if FUZZY_MATCHING_AVAILABLE:
        best_match, score = process.extractOne(
            query, qa_dict.keys(), scorer=fuzz.partial_ratio
        )
        if score >= threshold:
            logger.info(
                f"Found partial match: '{best_match}' with score {score} for query: '{query}'"
            )
            return best_match
    else:
        # Fallback to basic partial matching
        query_lower = query.lower()
        for stored_query in qa_dict.keys():
            if (
                query_lower in stored_query.lower()
                or stored_query.lower() in query_lower
            ):
                logger.info(
                    f"Found basic partial match: '{stored_query}' for query: '{query}'"
                )
                return stored_query

            # Check for word overlap as a simple fallback
            query_words = set(query_lower.split())
            stored_words = set(stored_query.lower().split())
            if (
                len(query_words & stored_words) / len(query_words) >= 0.5
            ):  # 50% word overlap
                logger.info(
                    f"Found word overlap match: '{stored_query}' for query: '{query}'"
                )
                return stored_query

    return None


def print_animated_message(message, speed=0.05):
    """Print message with animated typing effect"""
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()


def clean_search_query(prompt):
    """Extract search query from user input"""
    remove_words = ["jarvis", "wikipedia", "search", "for", "what", "is", "who"]
    query = prompt.lower()

    for word in remove_words:
        query = query.replace(word, "")

    return query.strip()


def is_cache_valid(cache_time):
    """Check if cache entry is still valid"""
    if not cache_time:
        return False
    time_diff = datetime.now() - datetime.fromisoformat(cache_time)
    return time_diff.total_seconds() < (CACHE_EXPIRY_HOURS * 3600)


def wiki_search(prompt, use_cache=True):
    """Search Wikipedia for information with caching"""
    search_prompt = clean_search_query(prompt)

    if not search_prompt:
        speak("Please specify what you want me to search for.")
        return

    # Check cache first
    if use_cache and search_prompt in wiki_cache:
        cache_entry = wiki_cache[search_prompt]
        if is_cache_valid(cache_entry.get("timestamp")):
            logger.info(f"Using cached result for: {search_prompt}")
            wiki_summary = cache_entry["summary"]

            # Display and speak the result
            animate_thread = threading.Thread(
                target=print_animated_message, args=(wiki_summary, 0.03)
            )
            speak_thread = threading.Thread(target=speak, args=(wiki_summary,))

            animate_thread.start()
            speak_thread.start()

            animate_thread.join()
            speak_thread.join()
            return

    try:
        # Set Wikipedia settings
        wikipedia.set_lang("en")
        wiki_summary = wikipedia.summary(
            search_prompt, sentences=1, auto_suggest=True, redirect=True
        )

        # Cache the result
        wiki_cache[search_prompt] = {
            "summary": wiki_summary,
            "timestamp": datetime.now().isoformat(),
        }

        # Display and speak the result using threads
        animate_thread = threading.Thread(
            target=print_animated_message, args=(wiki_summary, 0.03)
        )
        speak_thread = threading.Thread(target=speak, args=(wiki_summary,))

        animate_thread.start()
        speak_thread.start()

        animate_thread.join()
        speak_thread.join()

        # Save to Q&A database
        with qa_lock:
            qa_dict[search_prompt] = wiki_summary
            save_qa_data(qa_file_path, qa_dict)

    except wikipedia.exceptions.PageError:
        error_msg = f"Wikipedia doesn't have a page for '{search_prompt}'"
        logger.warning(error_msg)
        speak(f"I couldn't find information about {search_prompt} on Wikipedia.")
        google_search(search_prompt)
    except wikipedia.exceptions.DisambiguationError as e:
        options = e.options[:5]  # Get first 5 options
        error_msg = f"Multiple results found for '{search_prompt}'. Options: {', '.join(options)}"
        logger.info(error_msg)
        speak(
            f"There are multiple results for {search_prompt}. The top options are: {', '.join(options)}. Please be more specific."
        )
    except wikipedia.exceptions.WikipediaException as e:
        error_msg = f"Wikipedia error: {e}"
        logger.error(error_msg)
        speak("I'm having trouble accessing Wikipedia right now.")
        google_search(search_prompt)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg)
        speak("Sorry, I encountered an unexpected error while searching.")
        google_search(search_prompt)


def google_search(query):
    """Perform a Google search as fallback"""
    if not query:
        speak("I didn't understand what you want me to search for.")
        return

    # Clean the query
    query = clean_search_query(query)
    if not query:
        speak("I didn't understand what you want me to search for.")
        return

    encoded_query = quote(query)
    url = f"https://www.google.com/search?q={encoded_query}"

    try:
        webbrowser.open_new_tab(url)
        speak(f"Showing Google search results for {query} on your screen.")
        logger.info(f"Opened Google search for: {query}")
    except Exception as e:
        logger.error(f"Failed to open web browser: {e}")
        speak("I couldn't open the web browser. Please check your system settings.")


def brain(text, threshold=0.7):
    """Main function to process queries"""
    try:
        # Record user activity
        record_user_activity()

        # Check if query is in Q&A database first
        cleaned_text = clean_search_query(text)
        if cleaned_text in qa_dict:
            response = qa_dict[cleaned_text]
            speak(response)
            logger.info(f"Found answer in local database for: {cleaned_text}")
            return

        # Check for partial matches in Q&A database
        best_match = find_best_match(cleaned_text, qa_dict)
        if best_match:
            response = qa_dict[best_match]
            speak(response)
            logger.info(
                f"Found partial match answer in local database for: {cleaned_text} (matched: {best_match})"
            )
            return

        # Use AI model for response
        response = mind(text, threshold=threshold)

        if (
            response is None
            or not response.strip()
            or "i don't know" in response.lower()
            or "i'm not sure" in response.lower()
        ):

            logger.info(f"AI model couldn't answer, searching Wikipedia for: {text}")
            wiki_search(text)
            return

        # Speak the response and save to database
        speak(response)

        with qa_lock:
            qa_dict[cleaned_text] = response
            save_qa_data(qa_file_path, qa_dict)

        logger.info(f"Answered query using AI model: {text}")

    except Exception as e:
        error_msg = f"Error in brain function: {e}"
        logger.error(error_msg)
        speak("Sorry, I encountered an error while processing your request.")
        # Fallback to Wikipedia search
        wiki_search(text, use_cache=False)


# Add a function to clear cache if needed
def clear_wiki_cache():
    """Clear the Wikipedia cache"""
    global wiki_cache
    wiki_cache = {}
    logger.info("Wikipedia cache cleared")


if __name__ == "__main__":
    # Test the functions
    test_queries = [
        "what is artificial intelligence",
        "who is Albert Einstein",
        "explain quantum computing",
    ]

    for query in test_queries:
        print(f"\nTesting query: {query}")
        brain(query)
        time.sleep(2)  # Pause between queries
