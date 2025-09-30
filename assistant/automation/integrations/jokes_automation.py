from assistant.core.speak_selector import speak
import time
import pyjokes


def tell_joke():
    """
    Tell a randomly selected joke with robust error handling and retry logic.

    This function uses the pyjokes library to fetch and deliver programming-themed
    jokes. It includes comprehensive error handling to manage Unicode issues and
    other potential failures, with automatic retries for improved reliability.

    Features:
        - Automatic retry on failure (up to 3 attempts)
        - Unicode error handling for text-to-speech compatibility
        - Neutral category jokes (family-friendly content)
        - Progressive user feedback during retries

    Joke Source:
        Uses pyjokes library which provides a curated collection of
        programming-related jokes and puns suitable for technical audiences.

    Process:
        1. Announces joke delivery intent
        2. Fetches joke from pyjokes library (neutral category)
        3. Handles Unicode encoding issues with automatic retry
        4. Provides fallback messages if all attempts fail

    Example:
        >>> tell_joke()
        # Speaks: "Sure, here's a joke for you"
        # Speaks: "Why do programmers prefer dark mode? Because light attracts bugs!"

    Error Handling:
        - UnicodeEncodeError: Retries with different joke (common with special characters)
        - General Exceptions: Retries with incremental delay
        - All failures: Provides graceful fallback message

    Note:
        The 'neutral' category ensures jokes are appropriate for all audiences.
        Retry attempts include increasing delays to allow system recovery.
    """
    retry_attempts = 3
    sleep_duration = 1

    for attempt in range(retry_attempts):
        try:
            speak("Sure, here's a joke for you")
            time.sleep(0.5)  # Brief pause for natural delivery

            # Fetch a neutral-category joke (family-friendly)
            joke = pyjokes.get_joke(category="neutral")
            speak(joke)
            return  # Exit on successful joke delivery
        except UnicodeEncodeError:
            print(f"Unicode issue with joke (attempt {attempt+1})")
            if attempt < retry_attempts - 1:
                speak("Let me try a different joke.")
                time.sleep(sleep_duration)
                continue
            speak("Sorry, I can't tell that joke right now.")
        except Exception as e:
            print(f"Error telling joke (attempt {attempt+1}): {e}")
            if attempt < retry_attempts - 1:
                speak("Let me try again.")
                time.sleep(sleep_duration)
                continue
            speak("Sorry, I couldn't find a joke right now.")
