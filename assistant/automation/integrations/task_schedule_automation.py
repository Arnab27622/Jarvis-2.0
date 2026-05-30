"""
Module for managing persistent user memory, allowing the assistant to store,
retrieve, and summarize information using local JSON storage and LLM processing.
"""

import datetime
import json
import os
from assistant.core.config import config
from assistant.core.speak_selector import speak

# Path to the JSON file where remembered information is stored
JSON_FILE = str(config.remembered_info_path)

def _load_remembered_info() -> dict:
    """Reads and parses the persistent memory JSON file."""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def _save_remembered_info(data: dict) -> None:
    """Serializes and writes the memory dictionary to the JSON file."""
    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)


def remember_info(command_text: str) -> None:
    """
    Parses a command to extract information and saves it with a timestamp.
    """
    info = command_text.replace("remember that", "").strip()
    if info:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data = _load_remembered_info()
        data[timestamp] = info
        _save_remembered_info(data)
        
        speak("I've remembered that information")
    else:
        speak("What would you like me to remember?")


def recall_info(query: str = None) -> None:
    """
    Retrieves stored memory and uses an LLM to provide a conversational summary.
    """
    data = _load_remembered_info()
    
    if not data:
        speak("I don't have any information stored to recall")
        return

    api_key = config.gemini_api_key
    if not api_key:
        speak("I cannot access my thinking modules to analyze the memory.")
        return

    data_str = json.dumps(data, indent=2)
    prompt = (
        "You are Jarvis, a helpful AI assistant. The user asked you to recall "
        "what they told you to remember.\n"
    )
    
    if query and query.strip():
        prompt += f"The user specifically asked: '{query}'. Find the most relevant info and answer them concisely.\n"
    else:
        prompt += "Provide a brief, natural, conversational summary of the most relevant or recent items. Do not read every single timestamp or item, just give a helpful overview.\n"
    
    prompt += f"\nHere is your stored memory data (timestamps and notes):\n{data_str}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        import requests
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        summary = result['candidates'][0]['content']['parts'][0]['text']
        
        summary = summary.replace("*", "").replace("#", "")
        
        speak(summary)
        
    except Exception as e:
        print(f"Error accessing Gemini for recall: {e}")
        speak("I had trouble analyzing the memory file, but you do have notes saved.")


from assistant.core.registry import on_regex, on_fuzzy

@on_regex(r"remember\s+that\s+(?P<text>.*)$")
def handle_remember(text):
    """Regex handler for triggering the memory storage function."""
    remember_info(text)

@on_fuzzy(["what did i ask you to remember", "what do you remember", "recall"], score_cutoff=90)
def handle_recall():
    """Fuzzy match handler for triggering the memory recall function."""
    recall_info()
