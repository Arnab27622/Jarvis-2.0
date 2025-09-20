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


# Cache for Wikipedia results to avoid repeated API calls
wiki_cache = {}
CACHE_EXPIRY_HOURS = 24


def is_cache_valid(cache_time):
    """Check if cache entry is still valid"""
    if not cache_time:
        return False
    try:
        time_diff = datetime.now() - datetime.fromisoformat(cache_time)
        return time_diff.total_seconds() < (CACHE_EXPIRY_HOURS * 3600)
    except (ValueError, TypeError):
        return False


def wiki_search(prompt, use_cache=True):
    """Search Wikipedia for information with caching"""
    search_prompt = prompt

    if not search_prompt:
        speak("Please specify what you want me to search for.")
        return

    # Check cache first
    if use_cache and search_prompt in wiki_cache:
        cache_entry = wiki_cache[search_prompt]
        if is_cache_valid(cache_entry.get("timestamp")):
            print(f"Using cached result for: {search_prompt}")
            wiki_summary = cache_entry["summary"]

            speak(wiki_summary)
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

        speak(wiki_summary)

        # Save to Q&A database
        with qa_lock:
            qa_dict[search_prompt] = wiki_summary
            save_qa_data(qa_file_path, qa_dict)

    except wikipedia.exceptions.PageError:
        error_msg = f"Wikipedia doesn't have a page for '{search_prompt}'"
        print(error_msg)
        llm_response(search_prompt)
    except wikipedia.exceptions.DisambiguationError as e:
        options = e.options[:5]  # Get first 5 options
        speak(
            f"There are multiple results for {search_prompt}. The top options are: {', '.join(options)}. Please be more specific."
        )
    except wikipedia.exceptions.WikipediaException as e:
        error_msg = f"Wikipedia error: {e}"
        print(error_msg)
        llm_response(search_prompt)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        llm_response(search_prompt)
