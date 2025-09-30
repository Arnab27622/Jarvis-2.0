"""
LLM2 Module - Hugging Face Inference API Provider with Streaming Support

This module provides LLM functionality using Hugging Face's Inference API with
the GPT-OSS-20B model. It serves as a secondary fallback option in the LLM provider
hierarchy and includes both streaming and non-streaming response modes.

Key Features:
- Hugging Face Inference API integration
- Dual-mode operation (streaming and non-streaming)
- Advanced text cleaning and markdown stripping
- Robust content extraction from complex API responses
- Sentence segmentation for natural TTS streaming
- Conversation history management

Model: openai/gpt-oss-20b (via Hugging Face Inference API)
Capabilities: Text generation, conversation memory, streaming support

Dependencies:
- huggingface_hub: Hugging Face API client
- markdown: Markdown to HTML conversion
- beautifulsoup4: HTML parsing and text extraction
- strip_markdown: Markdown syntax removal
- python-dotenv: Environment variable management
"""

import sys
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from assistant.core.speak_selector import speak, speak_streaming
from assistant.activities.activity_monitor import record_user_activity
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)
import re

# Load environment variables from .env file
load_dotenv()

# Global conversation history with system prompt
conversation = [
    {
        "role": "system",
        "content": "You are Jarvis, a helpful AI assistant for a programmer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
    }
]


def clean_output_parser(raw: str) -> str:
    """
    Clean and normalize raw LLM output for TTS compatibility.

    Processes raw model output through multiple cleaning stages:
    1. Markdown to HTML conversion
    2. HTML tag stripping using BeautifulSoup
    3. Markdown syntax removal
    4. Whitespace normalization and cleanup

    Args:
        raw (str): Raw text output from LLM, potentially containing markdown

    Returns:
        str: Cleaned text suitable for text-to-speech

    Example:
        Input: "**Hello** world!\n\nThis is *important*."
        Output: "Hello world! This is important."
    """
    if raw is None:
        return ""

    # Convert Markdown to HTML for easier text extraction
    html = markdown.markdown(raw)

    # Use BeautifulSoup to parse HTML and extract clean text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")

    # Strip any remaining Markdown syntax
    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        # Fallback to original text if markdown stripping fails
        clean = text

    # Normalize whitespace and clean up formatting
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)  # Normalize multiple newlines
    clean = re.sub(r"[ \t]{2,}", " ", clean)  # Normalize multiple spaces/tabs

    return clean


def _extract_text_from_content(content) -> str:
    """
    Robustly extract text from complex HuggingFace API response structures.

    Handles various response formats from Hugging Face Inference API:
    - Simple string responses
    - Nested dictionary structures
    - List and tuple containers
    - Complex message objects

    Args:
        content: Raw content from API response, can be string, dict, list, or tuple

    Returns:
        str: Extracted and concatenated text content
    """
    if content is None:
        return ""

    # Direct string case
    if isinstance(content, str):
        return content

    pieces = []

    # Dictionary case - search for text-containing keys
    if isinstance(content, dict):
        for key in ("text", "content", "message", "value"):
            if key in content and isinstance(content[key], str):
                pieces.append(content[key])
        # Handle nested content lists
        if "content" in content and isinstance(content["content"], (list, tuple)):
            pieces.append(_extract_text_from_content(content["content"]))

        # Fallback: iterate through all values
        if not pieces:
            try:
                for v in content.values():
                    if isinstance(v, str):
                        pieces.append(v)
                    elif isinstance(v, (list, tuple, dict)):
                        pieces.append(_extract_text_from_content(v))
            except Exception:
                pieces.append(str(content))
        return " ".join([p for p in pieces if p])

    # List/tuple case - process each element
    if isinstance(content, (list, tuple)):
        for item in content:
            if item is None:
                continue
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                # Prefer 'text' key in dictionaries
                if "text" in item and isinstance(item["text"], str):
                    pieces.append(item["text"])
                elif "content" in item:
                    pieces.append(_extract_text_from_content(item["content"]))
                else:
                    # Search all values in dictionary
                    for v in item.values():
                        if isinstance(v, str):
                            pieces.append(v)
                        elif isinstance(v, (list, tuple, dict)):
                            pieces.append(_extract_text_from_content(v))
            else:
                pieces.append(str(item))
        return " ".join([p for p in pieces if p])

    # Fallback for any other type
    return str(content)


def split_into_sentences(text: str) -> list:
    """
    Split text into sentences for natural streaming TTS.

    Uses simple regex-based sentence boundary detection. For more accurate
    segmentation, consider integrating with NLTK or spaCy.

    Args:
        text (str): Continuous text to split into sentences

    Returns:
        list: List of sentences with proper punctuation

    Example:
        Input: "Hello world. How are you? I'm fine!"
        Output: ["Hello world.", "How are you?", "I'm fine!"]
    """
    # Simple sentence splitting using punctuation boundaries
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Add punctuation back to sentences
    sentences_with_punct = []
    for i, sentence in enumerate(sentences):
        if i < len(sentences) - 1:
            sentences_with_punct.append(sentence + ".")
        else:
            sentences_with_punct.append(sentence)

    return sentences_with_punct


def llm2(user_input):
    """
    Original non-streaming version of LLM2.

    Processes user input through Hugging Face Inference API and returns
    a complete response. Suitable for applications that don't require
    real-time streaming feedback.

    Args:
        user_input (str): User query or message to process

    Returns:
        str: Complete cleaned response text

    Workflow:
        1. Record user activity
        2. Add user message to conversation history
        3. Call Hugging Face Inference API
        4. Extract and clean response
        5. Update conversation history
        6. Speak response using TTS
        7. Store Q&A pair in database
    """
    record_user_activity()

    # Validate Hugging Face API token
    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Set the HF_TOKEN environment variable to your Hugging Face API token."
        )

    # Add user input to conversation context
    conversation.append({"role": "user", "content": user_input})

    # Initialize Hugging Face client and generate response
    client = InferenceClient(token=token)
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b", messages=conversation, max_tokens=1500
    )

    # Extract and process response
    raw_reply = response.choices[0].message.content
    raw_reply_str = _extract_text_from_content(raw_reply)
    reply = clean_output_parser(raw_reply_str)

    # Update conversation history with assistant response
    conversation.append({"role": "assistant", "content": reply})

    # Speak the response
    speak(reply)

    # Store in Q&A database for future reference
    with qa_lock:
        qa_dict[user_input] = reply
        save_qa_data(qa_file_path, qa_dict)

    return reply


def llm2_streaming(user_input):
    """
    Streaming version that processes and returns sentences for real-time TTS.

    Designed for interactive applications where immediate feedback is important.
    Returns pre-segmented sentences that can be streamed to TTS sequentially.

    Args:
        user_input (str): User query or message to process

    Returns:
        list: List of sentences ready for streaming TTS

    Workflow:
        1. Record user activity
        2. Add user message to conversation history
        3. Call Hugging Face Inference API
        4. Extract and clean response
        5. Update conversation history
        6. Split response into sentences
        7. Store Q&A pair in database
        8. Return sentences for streaming
    """
    record_user_activity()

    # Validate Hugging Face API token
    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Set the HF_TOKEN environment variable to your Hugging Face API token."
        )

    # Add user input to conversation context
    conversation.append({"role": "user", "content": user_input})

    # Initialize Hugging Face client and generate response
    client = InferenceClient(token=token)
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b", messages=conversation, max_tokens=1500
    )

    # Extract and process response
    raw_reply = response.choices[0].message.content
    raw_reply_str = _extract_text_from_content(raw_reply)
    reply = clean_output_parser(raw_reply_str)

    # Update conversation history with assistant response
    conversation.append({"role": "assistant", "content": reply})

    # Split into sentences for natural streaming TTS
    sentences = split_into_sentences(reply)

    # Store in Q&A database for future reference
    with qa_lock:
        qa_dict[user_input] = reply
        save_qa_data(qa_file_path, qa_dict)

    return sentences


if __name__ == "__main__":
    """
    Main execution block for testing LLM2 functionality.

    Provides an interactive command-line interface for testing
    both streaming and non-streaming modes of the Hugging Face
    Inference API integration.

    Usage:
        python llm2.py
        Enter your query: [user input]
        exit (to terminate)
    """
    while True:
        text = input("Enter your query: ")
        if text.strip() == "exit":
            print("Exiting...")
            sys.exit(0)
        else:
            # Use streaming version by default for testing
            sentences = llm2_streaming(text)
            speak_streaming(sentences)
