"""
LLM Search Module - Wrapper for Consolidated LLM Manager
"""

from assistant.core.speak_selector import wait_for_tts_completion

def llm_response_streaming(user_input: str):
    """Get streaming response from the consolidated LLM Manager."""
    from assistant.core.llm_manager import llm_response_streaming as manager_streaming
    sentences = manager_streaming(user_input)
    wait_for_tts_completion()
    return " ".join(sentences)

def llm_response(user_input: str) -> str:
    """Consolidated entry point for LLM responses."""
    from assistant.core.llm_manager import llm_response as manager_response
    return manager_response(user_input)

if __name__ == "__main__":
    import sys
    while True:
        user_input = input("Query: ")
        if user_input.lower() == "exit":
            sys.exit()
        llm_response_streaming(user_input)
