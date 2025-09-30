"""
LLM3 Module - OpenRouter API Provider with Real-time Streaming and Context Management

This module provides advanced LLM functionality using the OpenRouter API with
multiple model support, featuring sophisticated conversation history management
and real-time sentence streaming for natural dialogue interactions.

Key Features:
- OpenRouter API integration with multiple model support
- Real-time sentence-by-sentence streaming with intelligent segmentation
- Advanced conversation history management with automatic summarization
- Comprehensive text cleaning with Unicode normalization
- Context-aware conversation trimming to maintain performance
- Dual-mode operation (streaming and non-streaming)

Primary Model: x-ai/grok-4-fast:free (via OpenRouter)
Additional Models: Configurable through OpenRouter's model marketplace

Dependencies:
- requests: HTTP client for API communication
- markdown: Markdown to HTML conversion
- beautifulsoup4: HTML parsing and text extraction
- strip_markdown: Markdown syntax removal
- python-dotenv: Environment variable management
"""

import sys
import requests
import json
import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Optional
from assistant.core.speak_selector import speak_streaming, wait_for_tts_completion
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from assistant.activities.activity_monitor import record_user_activity
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)

# Load environment variables from .env file
load_dotenv()

# Default system prompt defining the AI assistant's personality and constraints
DEFAULT_SYSTEM_PROMPT = (
    "You are Jarvis, a helpful AI assistant for a programmer. "
    "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
    "Provide concise, accurate answers to questions. You answer questions, "
    "no matter how long, very quickly with low latency."
)

# Global, in-memory conversation state for maintaining context across interactions
CHAT_HISTORY: List[Dict[str, str]] = []


def simple_summarize(text: str, max_length: int = 200) -> str:
    """
    Simple context condensation to manage conversation history length.

    Truncates long text while preserving readability by breaking at word boundaries.
    Used to maintain conversation context without exceeding token limits.

    Args:
        text (str): Text content to summarize/truncate
        max_length (int): Maximum character length for output

    Returns:
        str: Truncated text with ellipsis if shortened

    Example:
        Input: "This is a very long sentence that needs to be shortened for context management"
        Output: "This is a very long sentence that needs to be..."
    """
    if len(text) <= max_length:
        return text
    else:
        # Truncate at the last space before max_length to avoid breaking words
        truncated = text[:max_length].rsplit(" ", 1)[0]
        return truncated + "..."


def clean_output_parser(raw: str) -> str:
    """
    Comprehensive text cleaning pipeline for LLM output.

    Processes raw model output through multiple stages:
    1. Markdown to HTML conversion
    2. HTML tag stripping using BeautifulSoup
    3. Markdown syntax removal
    4. Unicode character normalization
    5. Non-printable character removal
    6. Whitespace normalization

    Args:
        raw (str): Raw text output from LLM, potentially containing markdown and special characters

    Returns:
        str: Clean, TTS-ready text

    Example:
        Input: "**Hello** world! â This is *important*."
        Output: "Hello world! -- This is important."
    """
    if raw is None:
        return ""

    # Convert Markdown to HTML for structured text extraction
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

    # Normalize common Unicode artifacts and special characters
    replacements = {
        "â": "'",
        "ð": "",
        "â": '"',  # Left double quote
        "â": '"',  # Right double quote
        "â": "'",  # Left single quote
        "â": "'",  # Right single quote
        "â¦": "...",  # Ellipsis
        "â¢": "-",  # Bullet point
        "â": "--",  # Em dash
        "â": "-",  # En dash
    }

    for old, new in replacements.items():
        clean = clean.replace(old, new)

    # Remove non-printable characters while preserving extended Latin and common punctuation
    clean = re.sub(
        r"[^\x20-\x7E\u00A0-\u00FF\u2013\u2014\u2018\u2019\u201C\u201D]", "", clean
    )

    # Normalize whitespace and clean up formatting
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)  # Normalize multiple newlines
    clean = re.sub(r"[ \t]{2,}", " ", clean)  # Normalize multiple spaces/tabs

    return clean


def split_into_sentences(text: str) -> list:
    """
    Split text into sentences using improved boundary detection.

    Uses regex-based sentence splitting that handles common abbreviations
    and maintains proper punctuation for natural TTS flow.

    Args:
        text (str): Continuous text to split into sentences

    Returns:
        list: List of properly punctuated sentences

    Example:
        Input: "Hello world! How are you? I'm doing well."
        Output: ["Hello world!", "How are you?", "I'm doing well."]
    """
    # Improved sentence splitting that handles abbreviations and maintains context
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def trim_history(
    history: List[Dict[str, str]], max_messages: int = 12
) -> List[Dict[str, str]]:
    """
    Intelligent conversation history management with summarization.

    Maintains conversation context while preventing excessive token usage:
    - Preserves system message
    - Summarizes older messages
    - Keeps recent messages intact

    Args:
        history (List[Dict]): Complete conversation history
        max_messages (int): Maximum number of non-system messages to keep intact

    Returns:
        List[Dict]: Trimmed conversation history with summarized context
    """
    if not history:
        return history

    # Separate system message from conversation
    sys_msg = history[0] if history[0].get("role") == "system" else None
    non_system = history[1:] if sys_msg else history

    # Apply summarization if history exceeds limit
    if len(non_system) > max_messages:
        summarized_part = non_system[:-max_messages]
        summarized = []
        for msg in summarized_part:
            summarized.append(
                {
                    "role": msg["role"],
                    "content": simple_summarize(msg["content"], max_length=200),
                }
            )
        trimmed_non_system = summarized + non_system[-max_messages:]
    else:
        trimmed_non_system = non_system

    return ([sys_msg] if sys_msg else []) + trimmed_non_system


def llm3(
    conversation_history: List[Dict[str, str]],
    user_input: str,
    system_prompt: Optional[str] = DEFAULT_SYSTEM_PROMPT,
    model: str = "x-ai/grok-4-fast:free",
    max_tokens: int = 2048,
    temperature: float = 0.85,
    frequency_penalty: float = 0.34,
    presence_penalty: float = 0.06,
    repetition_penalty: float = 1.0,
    top_k: int = 0,
) -> str:
    """
    Original non-streaming version using OpenRouter API.

    Processes complete conversation in a single request and returns the full response.
    Suitable for applications where real-time streaming is not required.

    Args:
        conversation_history (List[Dict]): Current conversation context
        user_input (str): User's message to process
        system_prompt (str, optional): System context and personality definition
        model (str): OpenRouter model identifier
        max_tokens (int): Maximum tokens in response
        temperature (float): Creativity control (0.0-1.0)
        frequency_penalty (float): Penalize frequent tokens
        presence_penalty (float): Penalize new tokens
        repetition_penalty (float): Penalize repetition
        top_k (int): Top-k sampling parameter

    Returns:
        str: Complete cleaned response text

    Raises:
        requests.RequestException: If API request fails
    """
    record_user_activity()

    # Ensure system prompt is properly set in conversation history
    if system_prompt:
        if not conversation_history or conversation_history[0].get("role") != "system":
            conversation_history.insert(0, {"role": "system", "content": system_prompt})
        else:
            conversation_history[0]["content"] = system_prompt

    # Prepare API request headers with OpenRouter authentication
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    }

    # Construct API payload with conversation context and generation parameters
    payload = json.dumps(
        {
            "messages": conversation_history,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k,
            "stream": True,  # Always use streaming for consistent response handling
        }
    )

    try:
        # Send streaming request to OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=payload,
            stream=True,
        )

        # Process streaming response
        raw_completion = ""
        for line in response.iter_lines(decode_unicode=True, chunk_size=1024):
            if not line:
                continue
            modified_value: str = re.sub(r"^data:\s*", "", line)
            try:
                obj = json.loads(modified_value)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                if not delta:
                    continue
                piece = delta.get("content", "")
                raw_completion += piece
            except json.JSONDecodeError:
                continue

        # Clean and process the complete response
        clean_completion = clean_output_parser(raw_completion)

        # Update conversation history with assistant response
        conversation_history.append({"role": "assistant", "content": clean_completion})

        # Store in Q&A database for future reference
        with qa_lock:
            qa_dict[user_input] = clean_completion
            save_qa_data(qa_file_path, qa_dict)

        return clean_completion

    except requests.RequestException as e:
        return f"Failed to Get Response\nError: {e}\nResponse: {getattr(response, 'text', '')}"


def llm3_streaming(
    conversation_history: List[Dict[str, str]],
    user_input: str,
    system_prompt: Optional[str] = DEFAULT_SYSTEM_PROMPT,
    model: str = "x-ai/grok-4-fast:free",
    max_tokens: int = 2048,
    temperature: float = 0.85,
    frequency_penalty: float = 0.34,
    presence_penalty: float = 0.06,
    repetition_penalty: float = 1.0,
    top_k: int = 0,
) -> List[str]:
    """
    Real-time streaming version with sentence-by-sentence processing.

    Processes API response in real-time, extracting and cleaning sentences
    as they are generated for immediate TTS playback. Provides natural
    conversation flow with minimal latency.

    Args:
        conversation_history (List[Dict]): Current conversation context
        user_input (str): User's message to process
        system_prompt (str, optional): System context and personality definition
        model (str): OpenRouter model identifier
        max_tokens (int): Maximum tokens in response
        temperature (float): Creativity control (0.0-1.0)
        frequency_penalty (float): Penalize frequent tokens
        presence_penalty (float): Penalize new tokens
        repetition_penalty (float): Penalize repetition
        top_k (int): Top-k sampling parameter

    Returns:
        List[str]: List of cleaned sentences ready for streaming TTS

    Raises:
        requests.RequestException: If API request fails
    """
    record_user_activity()

    # Ensure system prompt is properly set in conversation history
    if system_prompt:
        if not conversation_history or conversation_history[0].get("role") != "system":
            conversation_history.insert(0, {"role": "system", "content": system_prompt})
        else:
            conversation_history[0]["content"] = system_prompt

    # Prepare API request headers with OpenRouter authentication
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    }

    # Construct API payload with conversation context and generation parameters
    payload = json.dumps(
        {
            "messages": conversation_history,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k,
            "stream": True,
        }
    )

    try:
        # Send streaming request to OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=payload,
            stream=True,
        )

        # Real-time sentence processing buffers
        current_sentence = ""
        sentences = []
        sentence_buffer = ""

        # Process streaming response in real-time
        for line in response.iter_lines(decode_unicode=True, chunk_size=1024):
            if not line:
                continue
            modified_value: str = re.sub(r"^data:\s*", "", line)
            try:
                obj = json.loads(modified_value)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                if not delta:
                    continue
                piece = delta.get("content", "")

                current_sentence += piece
                sentence_buffer += piece

                # Detect sentence boundaries for real-time TTS streaming
                if re.search(r"[.!?][\s]|$", sentence_buffer):
                    # Split buffer at sentence boundaries
                    potential_sentences = re.split(r"([.!?][\s])", sentence_buffer)

                    if len(potential_sentences) > 1:
                        # Reconstruct sentences with proper punctuation
                        reconstructed = []
                        for i in range(0, len(potential_sentences) - 1, 2):
                            if i + 1 < len(potential_sentences):
                                sentence_text = (
                                    potential_sentences[i] + potential_sentences[i + 1]
                                )
                                clean_sentence = clean_output_parser(
                                    sentence_text.strip()
                                )
                                # Only add substantial sentences (minimum length check)
                                if clean_sentence and len(clean_sentence) > 5:
                                    sentences.append(clean_sentence)
                                    reconstructed.append(sentence_text)

                        # Keep remaining text in buffer for next iteration
                        if len(potential_sentences) % 2 == 1:
                            sentence_buffer = potential_sentences[-1]
                        else:
                            sentence_buffer = ""

            except json.JSONDecodeError:
                continue

        # Process any remaining text in buffer as final sentence
        if sentence_buffer.strip():
            clean_sentence = clean_output_parser(sentence_buffer.strip())
            if clean_sentence:
                sentences.append(clean_sentence)

        # Construct full response from processed sentences
        full_response = " ".join(sentences)

        # Update conversation history with complete response
        conversation_history.append({"role": "assistant", "content": full_response})

        # Store in Q&A database for future reference
        with qa_lock:
            qa_dict[user_input] = full_response
            save_qa_data(qa_file_path, qa_dict)

        return sentences

    except requests.RequestException as e:
        error_msg = f"Failed to Get Response\nError: {e}\nResponse: {getattr(response, 'text', '')}"
        return [error_msg]


def llm3_text(text: str) -> str:
    """
    Simplified interface for non-streaming text processing.

    Wrapper function that manages global conversation history and provides
    a simple text-in, text-out interface for basic use cases.

    Args:
        text (str): User input text

    Returns:
        str: Complete cleaned response
    """
    CHAT_HISTORY.append({"role": "user", "content": text})
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)
    return llm3(CHAT_HISTORY, user_input=text, system_prompt=DEFAULT_SYSTEM_PROMPT)


def llm3_text_streaming(text: str) -> List[str]:
    """
    Simplified interface for streaming text processing.

    Wrapper function that manages global conversation history and provides
    a simple text-in, sentences-out interface for streaming use cases.

    Args:
        text (str): User input text

    Returns:
        List[str]: List of cleaned sentences for streaming TTS
    """
    CHAT_HISTORY.append({"role": "user", "content": text})
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)
    return llm3_streaming(
        CHAT_HISTORY, user_input=text, system_prompt=DEFAULT_SYSTEM_PROMPT
    )


if __name__ == "__main__":
    """
    Main execution block for testing LLM3 functionality.

    Provides an interactive command-line interface for testing
    the OpenRouter API integration with conversation history management.

    Commands:
        [text]: Process input text
        clear/reset: Clear conversation history
        exit/quit: Terminate program

    Usage:
        python llm3.py
    """
    while True:
        text_input = input("Enter your text: ")
        if text_input.strip().lower() in {"exit", "quit"}:
            sys.exit()
        elif text_input.strip().lower() in {"clear", "reset"}:
            CHAT_HISTORY.clear()
            print("Context cleared.")
            continue
        else:
            # Use streaming version by default for real-time testing
            sentences = llm3_text_streaming(text_input)
            speak_streaming(sentences)
            wait_for_tts_completion()
