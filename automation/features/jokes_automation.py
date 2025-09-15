from head.speak_selector import speak
import time
import pyjokes


def tell_joke():
    retry_attempts = 3
    sleep_duration = 1

    for attempt in range(retry_attempts):
        try:
            speak("Sure, here's a joke for you")
            time.sleep(0.5)

            joke = pyjokes.get_joke(category="neutral")
            speak(joke)
            return
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
