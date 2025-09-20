import sys
from assistant.LLM.model import mind
from assistant.activities.activity_monitor import record_user_activity
from assistant.core.speak_selector import speak
from assistant.automation.integrations.wiki_search import wiki_search
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)


def brain(text, threshold=0.7):
    """Main function to process queries"""
    try:
        # Record user activity
        record_user_activity()

        # Check if query is in Q&A database first
        if text in qa_dict:
            response = qa_dict[text]
            speak(response)
            return

        # Use local dataset for response first
        response = mind(text, threshold=threshold)

        if (
            response is None
            or not response.strip()
            or "i don't know" in response.lower()
            or "i'm not sure" in response.lower()
        ):
            wiki_search(text)
            return

        # Speak the response and save to database
        speak(response)

        with qa_lock:
            qa_dict[text] = response
            save_qa_data(qa_file_path, qa_dict)

    except Exception as e:
        error_msg = f"Error in brain function: {e}"
        print(error_msg)
        # Fallback to Wikipedia search
        wiki_search(text, use_cache=False)


if __name__ == "__main__":
    while True:
        text = input()

        if text == "exit":
            sys.exit()
        else:
            brain(text)
