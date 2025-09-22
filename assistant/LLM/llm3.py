import sys
import requests
import json
import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Optional
from assistant.core.speak_selector import speak
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

load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are Jarvis, a helpful AI assistant for a software engineer. "
    "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
    "Provide concise, accurate answers to questions. You answer questions, "
    "no matter how long, very quickly with low latency."
)

# Global, in-memory conversation state for context
CHAT_HISTORY: List[Dict[str, str]] = []


def simple_summarize(text: str, max_length: int = 200) -> str:
    """
    Simple context condensation to keep history messages short.
    Trims text to max_length characters, preserving whole words.
    """
    if len(text) <= max_length:
        return text
    else:
        truncated = text[:max_length].rsplit(" ", 1)[0]
        return truncated + "..."


def clean_output_parser(raw: str) -> str:
    """
    Clean the raw assistant output by:
    1. Converting Markdown to HTML.
    2. Parsing HTML to extract text (strip all tags).
    3. Optionally strip leftover Markdown if needed (for unusual cases).
    """
    if raw is None:
        return ""

    # 1) Convert Markdown to HTML (handles bold, italics, links, etc.)
    html = markdown.markdown(raw)

    # 2) Use BeautifulSoup to parse HTML and extract text
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(separator=" ")  # separator ensures words don’t concatenate

    # 3) Optionally strip Markdown syntax (if any left over)
    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        clean = text

    # 4) Normalize whitespace (collapse multiple spaces/newlines)
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean


def trim_history(
    history: List[Dict[str, str]], max_messages: int = 12
) -> List[Dict[str, str]]:
    """
    Keep the system message (if present) and the last `max_messages` non-system messages.
    Also summarize older messages to reduce payload size.
    """
    if not history:
        return history

    sys_msg = history[0] if history[0].get("role") == "system" else None
    non_system = history[1:] if sys_msg else history

    # Summarize messages older than the last max_messages
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
    max_tokens: int = 2048,  # reduced from 8096
    temperature: float = 0.85,
    frequency_penalty: float = 0.34,
    presence_penalty: float = 0.06,
    repetition_penalty: float = 1.0,
    top_k: int = 0,
) -> str:
    """
    Sends a request to the OpenRouter API and returns the generated text using the specified model.
    The system prompt is ensured at the beginning of the conversation history to guide the AI's behavior.
    """
    record_user_activity()

    # Ensure a single system prompt at index 0 (update if already present)
    if system_prompt:
        if not conversation_history or conversation_history[0].get("role") != "system":
            conversation_history.insert(0, {"role": "system", "content": system_prompt})
        else:
            conversation_history[0]["content"] = system_prompt

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    }

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
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=payload,
            stream=True,
        )

        raw_completion = ""
        for line in response.iter_lines(
            decode_unicode=True, chunk_size=1024
        ):  # increased chunk size
            if not line:
                continue
            modified_value: str = re.sub(r"^data:\s*", "", line)
            try:
                obj = json.loads(modified_value)
                # Defensive parsing for streaming deltas
                delta = obj.get("choices", [{}])[0].get("delta", {})
                if not delta:
                    continue
                piece = delta.get("content", "")
                raw_completion += piece
            except json.JSONDecodeError:
                # Ignore keepalives and non-JSON lines
                continue

        # Clean the output before appending
        clean_completion = clean_output_parser(raw_completion)

        # Append assistant reply to history for future context
        conversation_history.append({"role": "assistant", "content": clean_completion})

        speak(clean_completion)
        with qa_lock:
            qa_dict[user_input] = clean_completion
            save_qa_data(qa_file_path, qa_dict)

        return clean_completion

    except requests.RequestException as e:
        return f"Failed to Get Response\nError: {e}\nResponse: {getattr(response, 'text', '')}"


def llm3_text(text: str) -> str:
    """
    Add the user's message to global history, trim it, call llm3, and return the assistant's reply.
    """
    # Add user message to global history
    CHAT_HISTORY.append({"role": "user", "content": text})

    # Trim and summarize to keep context size manageable
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)

    # Sync trimmed content back to the global list to avoid unbounded growth
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)

    # Call the model with current context
    return llm3(CHAT_HISTORY, user_input=text, system_prompt=DEFAULT_SYSTEM_PROMPT)


if __name__ == "__main__":
    while True:
        text_input = input("Enter your text: ")
        if text_input.strip().lower() in {"exit", "quit"}:
            sys.exit()
        elif text_input.strip().lower() in {"clear", "reset"}:
            # Optional: clear chat history
            CHAT_HISTORY.clear()
            print("Context cleared.")
            continue
        else:
            llm3_text(text_input)
