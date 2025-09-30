"""
Brain Module - Main Processing Core for AI Assistant

This module serves as the central decision-making and processing unit for the AI assistant.
It orchestrates query processing, response generation, and data persistence by coordinating
between various subsystems including local Q&A database, local LLM, and external LLM fallback.

Key Features:
- User activity monitoring
- Local Q&A database lookup
- Local LLM response generation
- External LLM fallback for unknown queries
- Automatic learning and data persistence
- Thread-safe data operations
"""

import sys
from assistant.LLM.model import mind
from assistant.activities.activity_monitor import record_user_activity
from assistant.core.speak_selector import speak
from assistant.LLM.llm_search import llm_response
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)


def brain(text, threshold=0.7):
    """
    Main processing function that orchestrates query handling and response generation.

    This function implements a multi-tier response strategy:
    1. First checks local Q&A database for known answers
    2. Falls back to local LLM model for response generation
    3. Uses external LLM search as final fallback for unknown queries
    4. Automatically learns and stores new Q&A pairs

    Args:
        text (str): User input query to be processed
        threshold (float, optional): Confidence threshold for local LLM responses.
                                    Defaults to 0.7.

    Workflow:
        - Records user activity for monitoring
        - Checks local Q&A database for exact match
        - If no match, queries local LLM model
        - If local LLM returns uncertain response, falls back to external LLM
        - Stores successful local responses in Q&A database for future use

    Raises:
        Exception: Captures any processing errors and falls back to external LLM search
    """
    try:
        # Record user activity for monitoring and analytics
        record_user_activity()

        # Check if query exists in local Q&A database for instant response
        if text in qa_dict:
            response = qa_dict[text]
            speak(response)
            return

        # Use local dataset and model for primary response generation
        response = mind(text, threshold=threshold)

        # Validate response quality - check for empty or uncertain responses
        if (
            response is None
            or not response.strip()
            or "i don't know" in response.lower()
            or "i'm not sure" in response.lower()
        ):
            # Fallback to external LLM search for uncertain responses
            llm_response(text)
            return

        # Speak the validated response to user
        speak(response)

        # Store the new Q&A pair in local database for future use
        with qa_lock:  # Ensure thread-safe database operations
            qa_dict[text] = response
            save_qa_data(qa_file_path, qa_dict)

    except Exception as e:
        # Handle any processing errors gracefully
        error_msg = f"Error in brain function: {e}"
        print(error_msg)
        # Fallback to external LLM search in case of errors
        llm_response(text)


if __name__ == "__main__":
    """
    Main execution block for testing and direct module execution.

    Provides an interactive command-line interface for testing the brain function.
    Users can input queries and receive responses until they type 'exit'.

    Usage:
        python brain.py
        Query: [user input]
        Query: exit (to terminate)
    """
    while True:
        text = input("Query:")

        if text == "exit":
            sys.exit()
        else:
            brain(text)
