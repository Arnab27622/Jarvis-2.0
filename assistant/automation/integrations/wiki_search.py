from datetime import datetime
import wikipedia
from assistant.core.speak_selector import speak
from assistant.LLM.llm_search import llm_response
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)


# Cache for Wikipedia results to avoid repeated API calls and reduce latency
# Structure: {search_query: {"summary": str, "timestamp": iso_format_string}}
wiki_cache = {}
CACHE_EXPIRY_HOURS = 24  # Cache entries expire after 24 hours


def is_cache_valid(cache_time):
    """
    Validate whether a cached Wikipedia result is still within the expiry period.

    This function checks if a cache entry timestamp is still valid by comparing
    it against the current time and the configured cache expiry duration.

    Args:
        cache_time (str): ISO format timestamp string from cache entry

    Returns:
        bool: True if cache is still valid (within expiry period), False otherwise

    Example:
        >>> is_cache_valid("2024-01-15T10:30:00.000000")
        True  # If current time is within 24 hours of cache_time
    """
    if not cache_time:
        return False
    try:
        time_diff = datetime.now() - datetime.fromisoformat(cache_time)
        return time_diff.total_seconds() < (CACHE_EXPIRY_HOURS * 3600)
    except (ValueError, TypeError):
        return False


def wiki_search(prompt, use_cache=True):
    """
    Search Wikipedia for information with intelligent caching and fallback mechanisms.

    This function provides a robust Wikipedia search capability with multiple
    layers of functionality:
    - Caching to reduce API calls and improve response times
    - Automatic fallback to LLM when Wikipedia fails
    - Persistent storage of Q&A pairs for future reference
    - Comprehensive error handling for various Wikipedia exceptions

    Args:
        prompt (str): The search query or topic to look up on Wikipedia
        use_cache (bool): Whether to use cached results when available (default: True)

    Process Flow:
        1. Check cache for existing valid results
        2. If cache hit: return cached summary immediately
        3. If cache miss: query Wikipedia API
        4. On success: cache result, speak summary, save to Q&A database
        5. On failure: fall back to LLM for alternative response

    Cache Strategy:
        - Results cached in memory for 24 hours
        - Reduces Wikipedia API calls and improves response time
        - Cache key is the exact search prompt

    Error Handling:
        - PageError: No Wikipedia page found -> fallback to LLM
        - DisambiguationError: Multiple matches -> suggest top 5 options
        - WikipediaException: General Wikipedia errors -> fallback to LLM
        - General Exceptions: Unexpected errors -> fallback to LLM

    Example:
        >>> wiki_search("Albert Einstein")
        # Returns: "Albert Einstein was a German-born theoretical physicist..."
        >>> wiki_search("Python programming")
        # Returns: "Python is a high-level, general-purpose programming language..."

    Note:
        The function automatically saves successful searches to a persistent
        Q&A database for future reference and learning.
    """
    search_prompt = prompt

    # Validate input to ensure we have a search query
    if not search_prompt:
        speak("Please specify what you want me to search for.")
        return

    # Check cache first for improved performance
    if use_cache and search_prompt in wiki_cache:
        cache_entry = wiki_cache[search_prompt]
        if is_cache_valid(cache_entry.get("timestamp")):
            print(f"Using cached result for: {search_prompt}")
            wiki_summary = cache_entry["summary"]

            speak(wiki_summary)
            return

    try:
        # Configure Wikipedia for English language results
        wikipedia.set_lang("en")

        # Fetch Wikipedia summary with auto-suggest and redirect handling
        wiki_summary = wikipedia.summary(
            search_prompt,
            sentences=1,  # Limit to one sentence for concise responses
            auto_suggest=True,  # Allow Wikipedia to suggest similar topics
            redirect=True,  # Follow redirects to correct articles
        )

        # Cache the successful result with current timestamp
        wiki_cache[search_prompt] = {
            "summary": wiki_summary,
            "timestamp": datetime.now().isoformat(),
        }

        # Provide immediate voice feedback to user
        speak(wiki_summary)

        # Save to persistent Q&A database for future learning
        with qa_lock:  # Ensure thread-safe access to shared Q&A dictionary
            qa_dict[search_prompt] = wiki_summary
            save_qa_data(qa_file_path, qa_dict)

    except wikipedia.exceptions.PageError:
        """
        Handle case where Wikipedia doesn't have a page for the search term.

        This occurs when the search query doesn't match any Wikipedia article.
        We fall back to the LLM which can provide information from its training data.
        """
        error_msg = f"Wikipedia doesn't have a page for '{search_prompt}'"
        print(error_msg)
        llm_response(search_prompt)  # Fallback to language model

    except wikipedia.exceptions.DisambiguationError as e:
        """
        Handle ambiguous search terms that match multiple Wikipedia pages.

        This occurs when a search term could refer to multiple topics
        (e.g., "Python" could be programming language or snake species).
        We provide the top 5 options to help the user be more specific.
        """
        options = e.options[:5]  # Get first 5 options to avoid overwhelming user
        speak(
            f"There are multiple results for {search_prompt}. The top options are: {', '.join(options)}. Please be more specific."
        )

    except wikipedia.exceptions.WikipediaException as e:
        """
        Handle general Wikipedia API exceptions.

        This covers various Wikipedia-specific errors like rate limiting,
        network issues with Wikipedia, or other API-related problems.
        """
        error_msg = f"Wikipedia error: {e}"
        print(error_msg)
        llm_response(search_prompt)  # Fallback to language model

    except Exception as e:
        """
        Handle unexpected errors that aren't specific to Wikipedia.

        This is a catch-all for any other exceptions that might occur
        during the search process, ensuring the system remains stable.
        """
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        llm_response(search_prompt)  # Fallback to language model
