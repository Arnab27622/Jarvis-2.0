"""
LLM1 Module - GPT4Free Provider Implementation

This module provides LLM functionality using the GPT4Free (g4f) library with
the DeepSeek model. It serves as a tertiary fallback option in the LLM provider
hierarchy and includes web search capabilities for enhanced responses.

Key Features:
- DeepSeek model integration via GPT4Free
- Web search augmentation for current information
- Markdown stripping for clean text-to-speech
- Conversation history management
- Automatic Q&A database storage for learning

Model: deepseek-v3 (via GPT4Free)
Capabilities: Web search enabled, markdown cleanup, conversation memory

Dependencies:
- g4f: GPT4Free library for free LLM access
- strip_markdown: Clean markdown from responses for TTS
- activity_monitor: User interaction tracking
- save_data_locally: Persistent Q&A storage
"""

import sys
from g4f.client import Client
from assistant.core.speak_selector import speak
import strip_markdown
from assistant.activities.activity_monitor import record_user_activity
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)


def llm1(user_input):
    """
    Process user input using DeepSeek model via GPT4Free with web search.

    This function handles the complete LLM interaction pipeline including:
    - User activity recording
    - Conversation history management
    - Web-augmented response generation
    - Markdown cleanup for TTS
    - Response speaking and storage

    Args:
        user_input (str): User query or message to process

    Returns:
        None

    Workflow:
        1. Record user activity for analytics
        2. Initialize GPT4Free client with system prompt
        3. Send user query with web search enabled
        4. Clean markdown from response for clean TTS
        5. Speak response using selected TTS engine
        6. Store Q&A pair in local database for future use
    """
    # Track user interaction for analytics and monitoring
    record_user_activity()

    # Initialize GPT4Free client for DeepSeek model access
    client = Client()

    # System prompt defining AI personality and constraints
    system_prompt = (
        "You are Jarvis, a helpful AI assistant for a programmer. "
        "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
        "Provide concise, accurate answers to questions. "
        "You answer questions, no matter how long, very quickly with low latency."
    )

    # Initialize conversation history with system context
    conversation_history = [{"role": "system", "content": system_prompt}]

    # Add current user input to conversation history
    conversation_history.append({"role": "user", "content": user_input})

    # Generate response using DeepSeek model with web search
    response = client.chat.completions.create(
        model="deepseek-v3",  # DeepSeek V3 model
        messages=conversation_history,
        web_search=True,  # Enable web search for current information
    )

    # Extract and clean response content
    assistant_reply = strip_markdown.strip_markdown(
        response.choices[0].message.content.strip()
    )

    # Update conversation history with assistant response
    conversation_history.append({"role": "assistant", "content": assistant_reply})

    # Speak the cleaned response using TTS
    speak(assistant_reply)

    # Store the Q&A pair in local database for future reference
    with qa_lock:  # Thread-safe database operation
        qa_dict[user_input] = assistant_reply
        save_qa_data(qa_file_path, qa_dict)


if __name__ == "__main__":
    """
    Main execution block for testing LLM1 functionality independently.

    Provides an interactive command-line interface for testing
    the DeepSeek model integration and web search capabilities.

    Usage:
        python llm1.py
        [Enter query]
        exit (to terminate)
    """
    while True:
        user_input = input()

        if user_input == "exit":
            sys.exit()
        else:
            llm1(user_input=user_input)
