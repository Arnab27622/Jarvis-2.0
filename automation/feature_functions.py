import datetime
import os
import random
import re
from dotenv import load_dotenv
from urllib.parse import quote
import geocoder
import screen_brightness_control as sbc
import psutil
import webbrowser
import time
from head.mouth import speak
import pyautogui as ui
import pygetwindow as gw
import speedtest
from data.dlg_data.dlg import search_result
from googleapiclient.discovery import build

load_dotenv()


def handle_minimize():
    """Handle window minimization with improved reliability"""
    speak("Minimizing the window...")
    ui.hotkey("alt", "space")
    time.sleep(0.2)
    ui.press("n")


def handle_maximize():
    """Maximize the current window"""
    speak("Maximizing the window...")
    ui.hotkey("alt", "space")
    time.sleep(0.2)
    ui.press("x")


def handle_restore():
    """Restore window to normal size"""
    speak("Restoring the window...")
    # Use Alt+Space then R to restore (works in English OS)
    ui.hotkey("alt", "space")
    time.sleep(0.2)  # Small delay for menu to appear
    ui.press("r")


def handle_window_switch():
    """Switch between windows"""
    speak("Switching window")
    ui.hotkey("alt", "tab")
    time.sleep(0.5)


def handle_write(text):
    """Handle text writing commands"""
    speak("Writing...")
    write_text = text.replace("write", "").replace("right", "").strip()
    if write_text:
        ui.write(write_text)
    else:
        speak("I didn't hear any text to write")


def handle_volume_change(direction):
    """Handle volume changes with more controlled increments"""
    if direction == "increase":
        for _ in range(3):
            ui.press("volumeup")
        speak("Volume increased")
    else:
        for _ in range(3):
            ui.press("volumedown")
        speak("Volume decreased")


def handle_brightness(command_text):
    """Adjust screen brightness"""
    if "increase" in command_text or "up" in command_text:
        current_brightness = sbc.get_brightness()[0]
        new_brightness = min(100, current_brightness + 20)
        sbc.set_brightness(new_brightness)
        speak(f"Brightness increased to {new_brightness}%")
    elif "decrease" in command_text or "down" in command_text:
        current_brightness = sbc.get_brightness()[0]
        new_brightness = max(0, current_brightness - 20)
        sbc.set_brightness(new_brightness)
        speak(f"Brightness decreased to {new_brightness}%")
    else:
        current_brightness = sbc.get_brightness()[0]
        speak(f"Current brightness is {current_brightness}%")


def take_screenshot():
    """Take a screenshot and save it with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    screenshot = ui.screenshot()
    screenshot.save(filename)
    speak(f"Screenshot taken and saved as {filename}")


def handle_scroll(command_text):
    """Handle scroll commands with adjustable intensity"""
    # Determine scroll direction
    direction = -1 if "down" in command_text else 1

    # Detect intensity from command
    intensity = 1  # Default intensity
    if "little" in command_text or "bit" in command_text:
        intensity = 1
    elif "much" in command_text or "lot" in command_text:
        intensity = 5
    elif "page" in command_text:
        # Use page up/down keys instead of scrolling for larger movements
        if direction == 1:
            ui.press("pageup")
        else:
            ui.press("pagedown")
        speak("Page scrolled")
        return

    # Calculate scroll amount (adjust this value based on your needs)
    scroll_amount = 120 * intensity * direction  # 120 is a typical "click" amount

    # Perform the scroll
    ui.scroll(scroll_amount)

    # Provide feedback
    direction_text = "up" if direction == 1 else "down"
    speak(f"Scrolling {direction_text}")


def handle_scroll_to_top():
    """Scroll to the top of the page"""
    ui.hotkey("ctrl", "home")
    speak("Scrolled to top")


def handle_scroll_to_bottom():
    """Scroll to the bottom of the page"""
    ui.hotkey("ctrl", "end")
    speak("Scrolled to bottom")


def handle_web_search(command_text):
    """Perform a web search"""
    search_query = re.sub(
        r"\b(search|find|look up|for|in|on|google|web)\b",
        "",
        command_text,
        flags=re.IGNORECASE,
    ).strip()

    search_query = re.sub(r"\s+", " ", search_query).strip()

    if search_query:
        encoded_query = quote(search_query)
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        speak(f"{random.choice(search_result)} {search_query}")
    else:
        speak("What would you like me to search for?")


def tell_time():
    """Tell the current time"""
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The current time is {current_time}")


def tell_date():
    """Tell the current date"""
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today is {current_date}")


def get_system_info():
    """Get basic system information"""
    battery = psutil.sensors_battery()
    percent = battery.percent if battery else "unknown"
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    speak(f"Battery is at {percent} percent. Memory usage is {memory_percent} percent")


def open_incognito_tab():
    """Open an incognito/private browsing window - fixed version"""
    speak("Opening incognito window")

    if activate_browser():
        time.sleep(0.5)

        active_window = gw.getActiveWindow()
        if active_window:
            title = active_window.title.lower()

            if "firefox" in title:
                ui.hotkey("ctrl", "shift", "p")
            else:
                ui.hotkey("ctrl", "shift", "n")
        else:
            ui.hotkey("ctrl", "shift", "n")
    else:
        print("No browser found, opening Chrome in incognito mode")
        os.system("start chrome --incognito")


def bookmark_page():
    """Bookmark the current page"""
    speak("Bookmarking this page")
    ui.hotkey("ctrl", "d")
    time.sleep(0.5)
    ui.hotkey("enter")


def activate_browser():
    """Try to activate a browser window if one exists"""
    try:
        # Get all browser windows
        browsers = ["chrome", "firefox", "edge", "opera", "brave", "safari"]

        all_windows = gw.getAllWindows()

        # Find browser windows
        browser_windows = []
        for window in all_windows:
            if window.title:  # Check if window has a title
                title_lower = window.title.lower()
                if any(keyword in title_lower for keyword in browsers):
                    browser_windows.append(window)

        # Activate the first browser window found
        if browser_windows:
            browser_windows[0].activate()
            time.sleep(0.5)
            return True

        return False
    except Exception as e:
        print(f"Error activating browser: {e}")
        return False


def open_dev_tools():
    """Open developer tools"""
    speak("Opening developer tools")
    ui.hotkey("f12")


def toggle_fullscreen():
    """Toggle fullscreen mode"""
    speak("Toggling fullscreen")
    ui.hotkey("f11")


def reload_page():
    """Reload/refresh the current page"""
    speak("Reloading page")
    ui.hotkey("f5")


def go_back():
    """Go back to previous page"""
    speak("Going back")
    ui.hotkey("alt", "left")


def go_forward():
    """Go forward to next page"""
    speak("Going forward")
    ui.hotkey("alt", "right")


def duplicate_tab():
    """Duplicate the current tab"""
    speak("Duplicating tab")
    ui.hotkey("alt", "d")
    time.sleep(0.1)
    ui.hotkey("alt", "enter")


def get_current_location():
    """Get the current location using IP geolocation"""
    try:
        # Get location based on IP address
        g = geocoder.ip("me")

        if g.ok:
            city = g.city
            state = g.state
            country = g.country
            speak(
                f"Based on your IP address, you appear to be in {city}, {state}, {country}"
            )
        else:
            speak("Sorry, I couldn't determine your current location")
    except Exception as e:
        print(f"Error getting location: {e}")
        speak("Sorry, I'm having trouble determining your location")


# Memory feature variables
remembered_info = {}


def remember_info(command_text):
    """Remember information provided by the user"""
    info = command_text.replace("remember that", "").strip()
    if info:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        remembered_info[timestamp] = info
        speak("I've remembered that information")
    else:
        speak("What would you like me to remember?")


def recall_info():
    """Recall information that was remembered"""
    if remembered_info:
        speak("You asked me to remember the following:")
        for timestamp, info in remembered_info.items():
            speak(f"On {timestamp}, you said: {info}")
    else:
        speak("I don't have any information stored to recall")


def check_internet_speed():
    """Check and speak internet download and upload speeds"""

    try:
        speak("Testing your internet speed, this may take a moment...")

        # Create speedtest object with timeout
        st = speedtest.Speedtest()
        st.timeout = 60  # Set timeout to 60 seconds

        # Get the best server
        best_server = st.get_best_server()
        speak(
            f"Testing against server: {best_server['sponsor']} ({best_server['name']})"
        )

        # Test download speed
        speak("Measuring download speed...")
        download_speed = st.download() / 1_000_000  # Convert to Mbps

        # Test upload speed
        speak("Measuring upload speed...")
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps

        # Get ping and other details
        results = st.results.dict()
        ping_result = results["ping"]

        # Format results
        if download_speed > 50:
            speed_comment = "which is excellent"
        elif download_speed > 25:
            speed_comment = "which is good"
        elif download_speed > 10:
            speed_comment = "which is average"
        else:
            speed_comment = "which is below average"

        result_message = (
            f"Your internet speed test results: "
            f"Download: {download_speed:.2f} Mbps {speed_comment}, "
            f"Upload: {upload_speed:.2f} Mbps, "
            f"and Ping: {ping_result:.2f} milliseconds. "
        )

        speak(result_message)

    except speedtest.SpeedtestBestServerFailure:
        speak(
            "Could not find a suitable server for testing. Please check your internet connection."
        )
    except speedtest.SpeedtestException as e:
        error_msg = f"Speed test error: {str(e)}"
        print(error_msg)
        speak(
            "Sorry, the speed test failed. Please ensure you're connected to the internet."
        )
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        speak("An unexpected error occurred during the speed test.")


def play_on_youtube(search_query):
    """Search and play videos on YouTube using the official API"""
    try:
        remove_words = ["play", "youtube", "search", "for", "jarvis"]
        for word in remove_words:
            search_query = search_query.replace(word, "")
        search_query = search_query.strip()

        if not search_query:
            speak("What would you like me to play on YouTube?")
            return

        YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        request = youtube.search().list(
            part="snippet", maxResults=1, q=search_query, type="video"
        )
        response = request.execute()

        if response["items"]:
            video_id = response["items"][0]["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            speak(f"Playing {search_query} on YouTube")
            webbrowser.open(video_url)
        else:
            encoded_query = quote(search_query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            speak(
                f"No videos found for {search_query}. Showing search results instead."
            )

    except Exception as e:
        print(f"Error with YouTube API: {e}")
        encoded_query = quote(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        speak(f"Showing results for {search_query} on YouTube")
