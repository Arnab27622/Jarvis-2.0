"""
LLM4 Module - Phind-70B Model Integration with Advanced Context Management

This module provides integration with the Phind-70B model through their proprietary API,
featuring sophisticated conversation history management, streaming response processing,
and intelligent context optimization for technical programming assistance.

Key Features:
- Phind-70B model integration via official API endpoint
- Advanced conversation history management with automatic summarization
- Real-time streaming response processing
- Technical programming-focused optimization
- Comprehensive text cleaning and markdown normalization
- Context-aware conversation trimming for optimal performance

Model: Phind-70B (Specialized for programming and technical queries)
API Endpoint: https://https.extension.phind.com/agent/

Dependencies:
- requests: HTTP client for API communication
- markdown: Markdown to HTML conversion
- beautifulsoup4: HTML parsing and text extraction
- strip_markdown: Markdown syntax removal
- typing: Type hints for better code documentation
"""

import requests
import re
import json
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from typing import List, Dict
from assistant.core.speak_selector import speak
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)

# Global, in-memory conversation state for maintaining context across interactions
CHAT_HISTORY: List[Dict[str, str]] = []


def simple_summarize(text: str, max_length: int = 200) -> str:
    """
    Intelligent text condensation for conversation history optimization.

    Truncates long text while preserving semantic meaning by breaking at word boundaries.
    Used to maintain conversation context without exceeding API token limits or
    sacrificing important contextual information.

    Args:
        text (str): Text content to summarize/truncate
        max_length (int): Maximum character length for output (default: 200)

    Returns:
        str: Truncated text with ellipsis if shortened, preserving word boundaries

    Example:
        Input: "This is a very long technical explanation about Python decorators that needs shortening"
        Output: "This is a very long technical explanation about Python decorators that..."
    """
    if len(text) <= max_length:
        return text
    else:
        # Truncate at the last space before max_length to avoid breaking words
        truncated = text[:max_length].rsplit(" ", 1)[0]
        return truncated + "..."


def clean_output_parser(raw: str) -> str:
    """
    Comprehensive text cleaning pipeline optimized for Phind model output.

    Processes raw model output through multiple stages specifically tuned for
    technical and programming-focused responses:
    1. Markdown to HTML conversion for structured extraction
    2. HTML tag stripping using BeautifulSoup
    3. Markdown syntax removal fallback
    4. Whitespace normalization and cleanup

    Args:
        raw (str): Raw text output from Phind model, often containing markdown
                  formatting and technical notation

    Returns:
        str: Clean, TTS-ready text with preserved technical accuracy

    Example:
        Input: "**Python** decorators are `@wraps` functions that modify other functions."
        Output: "Python decorators are @wraps functions that modify other functions."
    """
    if raw is None:
        return ""

    # Convert Markdown to HTML for structured text extraction
    # This handles code blocks, bold, italics, links, and other formatting
    html = markdown.markdown(raw)

    # Use BeautifulSoup to parse HTML and extract clean text while preserving
    # important technical content like code snippets and technical terms
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")  # Maintain word separation

    # Strip any remaining Markdown syntax that wasn't converted to HTML
    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        # Fallback to original text if markdown stripping fails
        clean = text

    # Normalize whitespace and clean up formatting for optimal TTS
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)  # Preserve paragraph breaks
    clean = re.sub(r"[ \t]{2,}", " ", clean)  # Normalize excessive spacing

    return clean


def trim_history(
    history: List[Dict[str, str]], max_messages: int = 12
) -> List[Dict[str, str]]:
    """
    Advanced conversation history management with intelligent summarization.

    Optimizes conversation context for the Phind API by:
    - Preserving system message (personality context)
    - Summarizing older messages to reduce token usage
    - Maintaining recent messages intact for immediate context
    - Balancing context preservation with performance requirements

    Args:
        history (List[Dict]): Complete conversation history with role-content pairs
        max_messages (int): Maximum number of recent non-system messages to keep intact

    Returns:
        List[Dict]: Optimized conversation history with summarized context

    Note:
        The system message (if present) is always preserved as the first message
        as it defines the AI's personality and behavior constraints.
    """
    if not history:
        return history

    # Separate system message (personality definition) from conversation
    sys_msg = history[0] if history[0].get("role") == "system" else None
    non_system = history[1:] if sys_msg else history

    # Apply intelligent summarization when history exceeds optimization threshold
    if len(non_system) > max_messages:
        # Summarize older messages while preserving recent context
        summarized_part = non_system[:-max_messages]
        summarized = []
        for msg in summarized_part:
            summarized.append(
                {
                    "role": msg["role"],
                    "content": simple_summarize(msg["content"], max_length=200),
                }
            )
        # Combine summarized history with intact recent messages
        trimmed_non_system = summarized + non_system[-max_messages:]
    else:
        trimmed_non_system = non_system

    # Reconstruct full history with system message and optimized conversation
    return ([sys_msg] if sys_msg else []) + trimmed_non_system


def generate(
    prompt: List[Dict[str, str]],
    system_prompt: str = "You are Jarvis, a helpful AI assistant for a programmer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
    model: str = "Phind-70B",
    stream_chunk_size: int = 12,
    stream: bool = True,
) -> str:
    """
    Core generation function for Phind-70B model API integration.

    Handles the complete API interaction pipeline with the Phind model,
    including request formatting, streaming response processing, and
    response cleaning. Optimized for technical and programming queries.

    Args:
        prompt (List[Dict[str, str]]): Conversation history in OpenAI chat format
        system_prompt (str): System context defining AI personality and constraints
        model (str): Model identifier (default: "Phind-70B")
        stream_chunk_size (int): Bytes to read per streaming chunk (default: 12)
        stream (bool): Enable streaming response processing (default: True)

    Returns:
        str: Cleaned and processed model response

    Raises:
        requests.RequestException: If API request fails
        json.JSONDecodeError: If response parsing fails

    Note:
        The Phind API requires specific headers and payload structure that
        differ from standard OpenAI-compatible APIs.
    """
    # Phind API requires specific headers for proper authentication
    headers = {"User-Agent": ""}

    # Ensure system prompt is properly positioned in conversation history
    if system_prompt:
        if not prompt or prompt[0].get("role") != "system":
            prompt.insert(0, {"content": system_prompt, "role": "system"})
        else:
            prompt[0]["content"] = system_prompt

    # Construct API payload with Phind-specific parameters
    payload = {
        "additional_extension_context": "",
        "allow_magic_buttons": True,
        "is_vscode_extension": True,
        "message_history": prompt,
        "requested_model": model,
        "user_input": prompt[-1]["content"],  # Extract latest user input
    }

    # Send POST request to Phind API with streaming enabled
    chat_endpoint = "https://https.extension.phind.com/agent/"
    response = requests.post(chat_endpoint, headers=headers, json=payload, stream=True)

    # Process streaming response in real-time
    streaming_text = ""
    for value in response.iter_lines(decode_unicode=True, chunk_size=stream_chunk_size):
        modified_value = re.sub("data:", "", value)
        if modified_value:
            try:
                json_modified_value = json.loads(modified_value)
                if stream:
                    # Extract content from streaming response chunks
                    content = json_modified_value["choices"][0]["delta"]["content"]
                    streaming_text += content
            except:
                # Skip malformed JSON lines in stream
                continue

    # Clean the output through markdown formatting pipeline
    clean_completion = clean_output_parser(streaming_text)

    # Append assistant reply to history for future context continuity
    prompt.append({"role": "assistant", "content": clean_completion})

    return clean_completion


def llm4(text: str) -> str:
    """
    Primary interface function for Phind-70B model interactions.

    Provides a simplified text-in, response-out interface that handles:
    - Conversation history management
    - Context optimization and summarization
    - API communication
    - Response speaking and storage
    - Error handling and recovery

    Args:
        text (str): User input text/message to process

    Returns:
        str: Assistant's cleaned response text

    Workflow:
        1. Add user message to global conversation history
        2. Trim and optimize history to prevent context overflow
        3. Generate response using Phind-70B model
        4. Speak response using TTS system
        5. Store Q&A pair in local database for learning
    """
    # Add user message to global history for context continuity
    CHAT_HISTORY.append({"role": "user", "content": text})

    # Trim and summarize conversation history to maintain optimal context size
    # This prevents unbounded growth while preserving important contextual information
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)

    # Synchronize trimmed content back to global list
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)

    # Call the Phind model with current optimized context
    res = generate(
        prompt=CHAT_HISTORY.copy(),  # Pass copy to avoid modifying original during processing
        system_prompt="You are Jarvis, a helpful AI assistant for a software engineer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
        model="Phind-70B",
        stream=True,  # Always use streaming for consistent response handling
    )

    # Speak the response using the configured TTS system
    speak(res)

    # Store the Q&A pair in local database for future reference and learning
    with qa_lock:  # Ensure thread-safe database operation
        qa_dict[text] = res
        save_qa_data(qa_file_path, qa_dict)

    return res


if __name__ == "__main__":
    """
    Main execution block for testing Phind-70B model integration.

    Provides an interactive command-line interface for testing
    the Phind API integration with full conversation history management.

    Commands:
        [text]: Process input text through Phind-70B model
        clear/reset: Clear conversation history and context
        exit/quit: Terminate the testing session

    Usage:
        python llm4.py
        Enter your text: [user query]
    """
    while True:
        text_input = input("Enter your text: ")
        if text_input.strip().lower() in {"exit", "quit"}:
            break
        elif text_input.strip().lower() in {"clear", "reset"}:
            # Clear chat history to reset conversation context
            CHAT_HISTORY.clear()
            print("Context cleared.")
            continue
        else:
            # Process user input through Phind-70B model
            llm4(text_input)
