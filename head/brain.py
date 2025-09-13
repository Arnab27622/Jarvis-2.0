import wikipedia
import threading
import sys
import time
import webbrowser
import os
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from head.mouth import speak
from training_model.model import mind
from function.activity_monitor import record_user_activity

qa_lock = threading.Lock()


def load_qa_data(file_path):
    qa_dict = {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                if ":" in line:
                    q, a = line.split(":", 1)
                    qa_dict[q.strip()] = a.strip()
    except FileNotFoundError:
        print(f"QA data file not found: {file_path}")
    except Exception as e:
        print(f"Error loading QA data: {e}")

    return qa_dict


qa_file_path = current_dir.parent / "data" / "brain_data" / "qna_data.txt"
qa_dict = load_qa_data(qa_file_path)


def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.075)
    print()


def save_qa_data(file_path, qa_dict):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            for q, a in qa_dict.items():
                f.write(f"{q}:{a}\n")
    except Exception as e:
        print(f"Error saving QA data: {e}")


def wiki_search(prompt):
    search_prompt = (
        prompt.replace("jarvis", "")
        .replace("wikipedia", "")
        .replace("search", "")
        .strip()
    )

    if not search_prompt:
        speak("Please specify what you want me to search for.")
        return

    try:
        wiki_summary = wikipedia.summary(search_prompt, sentences=1, auto_suggest=False)

        animate_thread = threading.Thread(
            target=print_animated_message, args=(wiki_summary,)
        )
        speak_thread = threading.Thread(target=speak, args=(wiki_summary,))

        animate_thread.start()
        speak_thread.start()

        animate_thread.join()
        speak_thread.join()

        with qa_lock:
            qa_dict[search_prompt] = wiki_summary
            save_qa_data(qa_file_path, qa_dict)

    except wikipedia.exceptions.PageError:
        error_msg = f"Wikipedia doesn't have a page for '{search_prompt}'"
        print(error_msg)
        google_search(search_prompt)
    except wikipedia.exceptions.DisambiguationError as e:
        error_msg = f"Multiple results found for '{search_prompt}'. Please be more specific. Options include: {', '.join(e.options[:5])}"
        print(error_msg)
        speak(
            f"There are multiple results for {search_prompt}. Please be more specific."
        )
    except Exception as e:
        error_msg = f"Error fetching Wikipedia summary: {e}"
        print(error_msg)
        speak("Sorry, I couldn't fetch the information from Wikipedia.")
        google_search(search_prompt)


def google_search(query):
    query = (
        query.replace("who is", "")
        .replace("what is", "")
        .replace("search for", "")
        .strip()
    )

    if query:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open_new_tab(url)
        speak(f"Showing Google search results for {query} on your screen.")
    else:
        speak("I didn't understand what you want me to search for.")
        print("I didn't understand what you want me to search for.")


def brain(text):
    try:
        record_user_activity()
        response = mind(text, threshold=0.7)

        if (
            response is None
            or not response.strip()
            or "i don't know" in response.lower()
        ):
            wiki_search(text)
            return

        animate_thread = threading.Thread(
            target=print_animated_message, args=(response,)
        )
        speak_thread = threading.Thread(target=speak, args=(response,))

        animate_thread.start()
        speak_thread.start()

        animate_thread.join()
        speak_thread.join()

        with qa_lock:
            qa_dict[text] = response
            save_qa_data(qa_file_path, qa_dict)
    except Exception as e:
        print(f"An error occurred in brain function: {e}")
        speak("Sorry, I encountered an error while processing your request.")


if __name__ == "__main__":
    # Test the functions
    brain("what is hell")
