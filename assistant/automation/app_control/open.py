import pyautogui as ui
import webbrowser
import time
import random
import difflib
from assistant.core.speak_selector import speak
from data.dlg_data.dlg import open_dlg, open_website_maybe, sorry_web, websites


def appOpen(text: str) -> bool:
    """
    Open an application using the Windows Start menu search.

    This function automates the process of opening applications by:
    1. Using voice feedback to indicate what's being opened
    2. Opening the Start menu with Windows key
    3. Typing the application name
    4. Pressing Enter to launch the application

    Args:
        text (str): The name of the application to open (e.g., "notepad", "chrome")

    Returns:
        bool: True if the application opening process completed without errors,
              False if an exception occurred during the automation process.

    Note:
        The success of this function depends on the application being installed
        and accessible via Windows Start menu search. It does not verify if the
        application actually launched successfully.
    """
    try:
        speak(f"{random.choice(open_dlg)} {text}")
        ui.press("win")  # Open Start menu
        time.sleep(0.7)  # Wait for Start menu to open
        ui.write(text)  # Type application name
        time.sleep(0.5)  # Wait for search results
        ui.press("enter")  # Launch the application
        return True
    except Exception as e:
        speak(f"Failed to open application {text}. Error: {str(e)}")
        return False


def webOpen(text: str) -> bool:
    """
    Open a website in the default web browser.

    This function supports both exact website matches and fuzzy matching
    for similar website names. It first checks for exact matches in the
    predefined websites dictionary, then falls back to fuzzy matching.

    Args:
        text (str): The name or key of the website to open (e.g., "youtube", "google")

    Returns:
        bool: True if a website was successfully opened, False if no match was found.

    Process:
        1. Exact match: Opens immediately if found in websites dictionary
        2. Fuzzy match: Suggests closest match if similarity > 60%
        3. No match: Informs user that the website wasn't found
    """
    text = text.lower().strip()

    # Check for exact match in predefined websites
    if text in websites:
        speak(f"{random.choice(open_dlg)} {text}")
        webbrowser.open(websites[text])
        return True

    # Fuzzy matching for similar website names
    matches = difflib.get_close_matches(text, websites.keys(), n=1, cutoff=0.6)
    if matches:
        closest_match = matches[0]
        speak(f"{random.choice(open_website_maybe)} {closest_match}")
        webbrowser.open(websites[closest_match])
        return True

    # No matching website found
    speak(f"{random.choice(sorry_web)} {text}")
    return False


def open_command(text: str) -> None:
    """
    Main command handler for opening applications or websites.

    This intelligent function determines whether the user wants to open
    an application or a website and routes the request accordingly.

    Strategy:
    1. First checks if the text matches a known website (exact or fuzzy)
    2. If not a known website, attempts to open as an application
    3. If application opening fails, tries website opening as fallback
    4. Provides comprehensive error handling and user feedback

    Args:
        text (str): The name of the application or website to open.
                   Can be a website key (e.g., "youtube") or application
                   name (e.g., "notepad").

    Examples:
        >>> open_command("youtube")
        # Opens YouTube in web browser

        >>> open_command("notepad")
        # Opens Notepad application

        >>> open_command("photoshop")
        # Opens Photoshop if installed, otherwise tries website

    Note:
        The function will provide voice feedback at each step to keep the
        user informed about what's happening.
    """
    clean_text = text.lower().strip()

    # Validate input
    if clean_text == "":
        speak("Please specify what you want to open.")
        return

    # Check if it's a known website (exact match or fuzzy match)
    is_known_website = clean_text in websites or difflib.get_close_matches(
        clean_text, websites.keys(), n=1, cutoff=0.6
    )

    if is_known_website:
        webOpen(text)
    else:
        # Try to open as application first
        app_success = appOpen(clean_text)

        # If app opening fails, try as a website (might be an unknown website)
        if not app_success:
            web_success = webOpen(text)

            # If both methods fail, provide comprehensive error message
            if not web_success:
                speak(f"I couldn't find an application or website named {clean_text}.")


if __name__ == "__main__":
    """
    Test function for the open command system.

    When run as a standalone script, this tests the open_command function
    with a sample input to verify the system is working correctly.
    """
    open_command("open abc")
