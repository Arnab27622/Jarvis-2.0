import datetime
import json
import os
from assistant.core.speak_selector import speak

# Path to the JSON file where remembered information is stored
JSON_FILE = r"C:\Users\ARNAB DEY\MyPC\Python\Projects\Jarvis 2.0\data\remembered_info.json"

def _load_remembered_info() -> dict:
    """Load the remembered information from the JSON file."""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def _save_remembered_info(data: dict) -> None:
    """Save the remembered information to the JSON file."""
    # Ensure the directory exists before saving
    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)


def remember_info(command_text: str) -> None:
    """
    Store user-provided information with automatic timestamping for later recall.

    This function extracts information from voice commands and stores it in a
    persistent JSON file with the current timestamp as the key. Useful for
    remembering notes, reminders, or important information across sessions.

    Args:
        command_text (str): The voice command containing information to remember.
                          Expected format: "remember that [information]"

    Process:
        1. Extracts information by removing the "remember that" trigger phrase
        2. Generates a timestamp for when the information was stored
        3. Loads existing data from remembered_info.json
        4. Adds the new information to the dictionary
        5. Saves the updated dictionary back to the JSON file
        6. Provides voice confirmation of successful storage

    Example:
        >>> remember_info("remember that my meeting is at 3 PM tomorrow")
        # Stores: {'2024-01-15 14:30:25': 'my meeting is at 3 PM tomorrow'}
        # Speaks: "I've remembered that information"

    Storage:
        Information is persistently stored in data/remembered_info.json and 
        will survive application restarts.
    """
    # Extract the actual information by removing the command trigger phrase
    info = command_text.replace("remember that", "").strip()
    if info:
        # Create timestamp in human-readable format for easy recall
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Load existing data, add new entry, and save
        data = _load_remembered_info()
        data[timestamp] = info
        _save_remembered_info(data)
        
        speak("I've remembered that information")
    else:
        speak("What would you like me to remember?")


def recall_info(query: str = None) -> None:
    """
    Recall stored information using an LLM for semantic summarization.

    Instead of reading the entire JSON file verbatim, this sends the data to 
    Gemini 3.1 Flash Lite to provide a concise, natural summary of the notes,
    or to answer specific questions about the stored data.
    """
    data = _load_remembered_info()
    
    if not data:
        speak("I don't have any information stored to recall")
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        speak("I cannot access my thinking modules to analyze the memory.")
        return

    # Prepare prompt for the LLM
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
        
        # Clean up Markdown for text-to-speech
        summary = summary.replace("*", "").replace("#", "")
        
        speak(summary)
        
    except Exception as e:
        print(f"Error accessing Gemini for recall: {e}")
        speak("I had trouble analyzing the memory file, but you do have notes saved.")
