# llm_search.py (modified for queue-based streaming)
import sys
from assistant.LLM.llm2 import llm2_streaming as llm2_streaming_func
from assistant.LLM.llm1 import llm1 as llm1_streaming_func
from assistant.LLM.llm3 import llm3_text_streaming as llm3_streaming_func

from assistant.LLM.llm4 import llm4 as llm4_streaming_func
from assistant.core.speak_selector import speak_streaming, wait_for_tts_completion


def llm_response_streaming(user_input: str):
    """Get streaming response from LLMs and speak sentences as they come"""
    try:
        # Try llm3 first
        print("Using LLM3...")
        sentences = llm3_streaming_func(user_input)
        speak_streaming(sentences)
        wait_for_tts_completion()  # Wait for all speech to finish
        return " ".join(sentences)
    except Exception as e:
        print(f"LLM3 failed: {e}")
        try:
            # Fallback to llm2 on failure
            print("Using LLM2...")
            sentences = llm2_streaming_func(user_input)
            speak_streaming(sentences)
            wait_for_tts_completion()  # Wait for all speech to finish
            return " ".join(sentences)
        except Exception as e2:
            print(f"LLM2 failed: {e2}")
            # Fallback to llm1 on failure
            print("Using LLM1...")
            sentences = llm1_streaming_func(user_input)
            speak_streaming(sentences)
            wait_for_tts_completion()  # Wait for all speech to finish
            return " ".join(sentences)


def llm_response(user_input: str) -> str:
    """Legacy function - now uses streaming internally"""
    return llm_response_streaming(user_input)


if __name__ == "__main__":
    while True:
        user_input = input()
        if user_input == "exit":
            sys.exit()
        else:
            llm_response_streaming(user_input=user_input)
