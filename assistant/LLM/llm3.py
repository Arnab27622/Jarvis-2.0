# llm3.py (modified for real-time sentence streaming)
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

load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are Jarvis, a helpful AI assistant for a programmer. "
    "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
    "Provide concise, accurate answers to questions. You answer questions, "
    "no matter how long, very quickly with low latency."
)

# Global, in-memory conversation state for context
CHAT_HISTORY: List[Dict[str, str]] = []


def simple_summarize(text: str, max_length: int = 200) -> str:
    """Simple context condensation to keep history messages short."""
    if len(text) <= max_length:
        return text
    else:
        truncated = text[:max_length].rsplit(" ", 1)[0]
        return truncated + "..."


def clean_output_parser(raw: str) -> str:
    """Clean the raw assistant output"""
    if raw is None:
        return ""

    # Convert Markdown to HTML
    html = markdown.markdown(raw)

    # Use BeautifulSoup to parse HTML and extract text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")

    # Strip Markdown syntax
    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        clean = text

    # Normalize Unicode characters and remove unwanted symbols
    replacements = {
        "â": "'",
        "ð": "",
        "â": '"',
        "â": '"',
        "â": "'",
        "â": "'",
        "â¦": "...",
        "â¢": "-",
        "â": "--",
        "â": "-",
    }

    for old, new in replacements.items():
        clean = clean.replace(old, new)

    # Remove non-printable characters
    clean = re.sub(
        r"[^\x20-\x7E\u00A0-\u00FF\u2013\u2014\u2018\u2019\u201C\u201D]", "", clean
    )

    # Normalize whitespace
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean


def split_into_sentences(text: str) -> list:
    """Split text into sentences for streaming"""
    # Improved sentence splitting that handles abbreviations
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def trim_history(
    history: List[Dict[str, str]], max_messages: int = 12
) -> List[Dict[str, str]]:
    """Keep the system message and the last `max_messages` non-system messages."""
    if not history:
        return history

    sys_msg = history[0] if history[0].get("role") == "system" else None
    non_system = history[1:] if sys_msg else history

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
    """Original non-streaming version"""
    record_user_activity()

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

        clean_completion = clean_output_parser(raw_completion)

        conversation_history.append({"role": "assistant", "content": clean_completion})

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
    """Streaming version that returns sentences as they are generated"""
    record_user_activity()

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

        current_sentence = ""
        sentences = []
        sentence_buffer = ""

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

                # Check if we have a complete sentence (ending with .!? followed by space or end)
                if re.search(r"[.!?][\s]|$", sentence_buffer):
                    # Look for sentence boundaries in the buffer
                    potential_sentences = re.split(r"([.!?][\s])", sentence_buffer)

                    if len(potential_sentences) > 1:
                        # Reconstruct sentences with their punctuation
                        reconstructed = []
                        for i in range(0, len(potential_sentences) - 1, 2):
                            if i + 1 < len(potential_sentences):
                                sentence_text = (
                                    potential_sentences[i] + potential_sentences[i + 1]
                                )
                                clean_sentence = clean_output_parser(
                                    sentence_text.strip()
                                )
                                if (
                                    clean_sentence and len(clean_sentence) > 5
                                ):  # Minimum sentence length
                                    sentences.append(clean_sentence)
                                    reconstructed.append(sentence_text)

                        # Keep the remaining text in buffer
                        if len(potential_sentences) % 2 == 1:
                            sentence_buffer = potential_sentences[-1]
                        else:
                            sentence_buffer = ""

            except json.JSONDecodeError:
                continue

        # Add any remaining text as the final sentence
        if sentence_buffer.strip():
            clean_sentence = clean_output_parser(sentence_buffer.strip())
            if clean_sentence:
                sentences.append(clean_sentence)

        # Join all sentences for the full response
        full_response = " ".join(sentences)

        conversation_history.append({"role": "assistant", "content": full_response})

        with qa_lock:
            qa_dict[user_input] = full_response
            save_qa_data(qa_file_path, qa_dict)

        return sentences

    except requests.RequestException as e:
        error_msg = f"Failed to Get Response\nError: {e}\nResponse: {getattr(response, 'text', '')}"
        return [error_msg]


def llm3_text(text: str) -> str:
    """Original non-streaming version"""
    CHAT_HISTORY.append({"role": "user", "content": text})
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)
    return llm3(CHAT_HISTORY, user_input=text, system_prompt=DEFAULT_SYSTEM_PROMPT)


def llm3_text_streaming(text: str) -> List[str]:
    """Streaming version that returns sentences"""
    CHAT_HISTORY.append({"role": "user", "content": text})
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)
    return llm3_streaming(
        CHAT_HISTORY, user_input=text, system_prompt=DEFAULT_SYSTEM_PROMPT
    )


if __name__ == "__main__":
    while True:
        text_input = input("Enter your text: ")
        if text_input.strip().lower() in {"exit", "quit"}:
            sys.exit()
        elif text_input.strip().lower() in {"clear", "reset"}:
            CHAT_HISTORY.clear()
            print("Context cleared.")
            continue
        else:
            # Use streaming version by default
            sentences = llm3_text_streaming(text_input)
            speak_streaming(sentences)
            wait_for_tts_completion()
