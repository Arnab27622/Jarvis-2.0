"""
LLM Search Module - Multi-Provider LLM Orchestration with Fallback System

This module provides a robust, multi-layered approach to Large Language Model interactions
with automatic fallback between different LLM providers. It implements a streaming-first
architecture that processes and speaks responses in real-time.

Key Features:
- Cascading fallback system across multiple LLM providers
- Streaming response processing for real-time interaction
- Sentence-by-sentence TTS for natural conversation flow
- Automatic provider switching on failure
- Legacy compatibility with non-streaming interface

Fallback Hierarchy:
    1. Primary: LLM2 (Highest priority)
    2. Secondary: LLM3 (Medium priority)
    3. Tertiary: LLM1 (Lowest priority)

Usage:
    from assistant.LLM.llm_search import llm_response, llm_response_streaming

Dependencies:
- llm1, llm2, llm3, llm4: Individual LLM provider implementations
- speak_selector: Dynamic TTS engine selection
- sys: System utilities for exit handling
"""

import sys
from assistant.LLM.llm2 import llm2_streaming as llm2_streaming_func
from assistant.LLM.llm1 import llm1 as llm1_streaming_func
from assistant.LLM.llm3 import llm3_text_streaming as llm3_streaming_func
from assistant.LLM.llm4 import llm4 as llm4_streaming_func
from assistant.core.speak_selector import speak_streaming, wait_for_tts_completion


def llm_response_streaming(user_input: str):
    """
    Get streaming response from LLMs with cascading fallback and real-time TTS.

    Processes user input through multiple LLM providers in a priority-based
    fallback chain. Streams responses sentence-by-sentence for natural
    conversation flow and immediate feedback.

    Args:
        user_input (str): User query or message to process

    Returns:
        str: Complete response text from the successful LLM provider

    Workflow:
        1. Attempt LLM2 (primary provider)
        2. If LLM2 fails, fallback to LLM3 (secondary provider)
        3. If LLM3 fails, fallback to LLM1 (tertiary provider)
        4. Stream sentences to TTS as they become available
        5. Wait for all TTS to complete before returning

    Raises:
        Exception: If all LLM providers fail, the exception from LLM1 propagates
    """
    try:
        # Try llm2 first (highest priority provider)
        print("Using LLM2...")
        sentences = llm2_streaming_func(user_input)
        speak_streaming(sentences)
        wait_for_tts_completion()  # Ensure all speech finishes before continuing
        return " ".join(sentences)
    except Exception as e:
        print(f"LLM3 failed: {e}")
        try:
            # Fallback to llm3 on failure (secondary provider)
            print("Using LLM3...")
            sentences = llm3_streaming_func(user_input)
            speak_streaming(sentences)
            wait_for_tts_completion()  # Ensure all speech finishes before continuing
            return " ".join(sentences)
        except Exception as e2:
            print(f"LLM3 failed: {e2}")
            # Final fallback to llm1 (tertiary provider)
            print("Using LLM1...")
            sentences = llm1_streaming_func(user_input)
            speak_streaming(sentences)
            wait_for_tts_completion()  # Ensure all speech finishes before continuing
            return " ".join(sentences)


def llm_response(user_input: str) -> str:
    """
    Legacy compatibility function - maintains backward compatibility.

    Provides the same interface as previous non-streaming versions while
    internally using the new streaming architecture. Ensures existing
    code continues to work without modification.

    Args:
        user_input (str): User query or message to process

    Returns:
        str: Complete response text from the successful LLM provider
    """
    return llm_response_streaming(user_input)


if __name__ == "__main__":
    """
    Main execution block for testing LLM search functionality.

    Provides an interactive command-line interface for testing
    the multi-provider LLM system with real-time TTS.

    Usage:
        python llm_search.py
        [Enter query]
        exit (to terminate)
    """
    while True:
        user_input = input()
        if user_input == "exit":
            sys.exit()
        else:
            llm_response_streaming(user_input=user_input)
