"""
LLM3 Module - OpenRouter API Provider with Real-time Streaming and Context Management
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

load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are Jarvis, a helpful AI assistant for a programmer. "
    "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
    "Provide concise, accurate answers to questions. You answer questions, "
    "no matter how long, very quickly with low latency."
)

CHAT_HISTORY: List[Dict[str, str]] = []


def simple_summarize(text: str, max_length: int = 200) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length].rsplit(" ", 1)[0]
    return truncated + "..."


def clean_output_parser(raw: str) -> str:
    if raw is None:
        return ""

    html = markdown.markdown(raw)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")

    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        clean = text

    replacements = {
        "â": "'",
        "ð": "",
        "â": '"',
        "â": '"',
        "â": "'",
        "â": "'",
        "â¦": "...",
        "â¢": "-",
        "â": "--",
        "â": "-",
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)

    clean = re.sub(
        r"[^\x20-\x7E\u00A0-\u00FF\u2013\u2014\u2018\u2019\u201C\u201D]", "", clean
    )
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean


def split_into_sentences(text: str) -> list:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def trim_history(
    history: List[Dict[str, str]], max_messages: int = 12
) -> List[Dict[str, str]]:
    if not history:
        return history

    sys_msg = history[0] if history[0].get("role") == "system" else None
    non_system = history[1:] if sys_msg else history

    if len(non_system) > max_messages:
        summarized_part = non_system[:-max_messages]
        summarized = [
            {"role": msg["role"], "content": simple_summarize(msg["content"], 200)}
            for msg in summarized_part
        ]
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

    payload = json.dumps({
        "messages": conversation_history,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "repetition_penalty": repetition_penalty,
        "top_k": top_k,
        "stream": True,
    })

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=payload,
            stream=True,
        )
        response.raise_for_status()

        raw_completion = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                obj = json.loads(data_str)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content", "")
                if piece:
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
        return f"Failed to Get Response\nError: {e}"


def llm3_streaming(
    conversation_history: List[Dict[str, str]],
    user_input: str,
    system_prompt: Optional[str] = DEFAULT_SYSTEM_PROMPT,
    model: str = "openai/gpt-oss-120b:free",
    max_tokens: int = 2048,
    temperature: float = 0.85,
    frequency_penalty: float = 0.34,
    presence_penalty: float = 0.06,
    repetition_penalty: float = 1.0,
    top_k: int = 0,
) -> List[str]:
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

    payload = json.dumps({
        "messages": conversation_history,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "repetition_penalty": repetition_penalty,
        "top_k": top_k,
        "stream": True,
    })

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=payload,
            stream=True,
        )
        response.raise_for_status()

        sentences = []
        sentence_buffer = ""

        for line in response.iter_lines(decode_unicode=True):
            # Skip empty lines and non-data lines
            if not line or not line.startswith("data:"):
                continue

            data_str = line[len("data:"):].strip()

            # Stream end marker
            if data_str == "[DONE]":
                break

            try:
                obj = json.loads(data_str)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content", "")
                if not piece:
                    continue

                sentence_buffer += piece

                # Check for sentence-ending punctuation followed by whitespace
                # FIX: removed the broken `|$` which caused every chunk to trigger this
                while re.search(r"[.!?]\s", sentence_buffer):
                    # Split on the first sentence boundary only
                    match = re.search(r"[.!?]\s", sentence_buffer)
                    end_idx = match.end()  # include the space after punctuation

                    sentence_text = sentence_buffer[:end_idx].strip()
                    sentence_buffer = sentence_buffer[end_idx:]

                    clean_sentence = clean_output_parser(sentence_text)
                    if clean_sentence and len(clean_sentence) > 5:
                        sentences.append(clean_sentence)

            except json.JSONDecodeError:
                continue

        # Process any remaining text in the buffer
        if sentence_buffer.strip():
            clean_sentence = clean_output_parser(sentence_buffer.strip())
            if clean_sentence:
                sentences.append(clean_sentence)

        full_response = " ".join(sentences)

        conversation_history.append({"role": "assistant", "content": full_response})

        with qa_lock:
            qa_dict[user_input] = full_response
            save_qa_data(qa_file_path, qa_dict)

        return sentences

    except requests.RequestException as e:
        return [f"Failed to Get Response\nError: {e}"]


def llm3_text(text: str) -> str:
    CHAT_HISTORY.append({"role": "user", "content": text})
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)
    return llm3(CHAT_HISTORY, user_input=text, system_prompt=DEFAULT_SYSTEM_PROMPT)


def llm3_text_streaming(text: str) -> List[str]:
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
            sentences = llm3_text_streaming(text_input)
            speak_streaming(sentences)
            wait_for_tts_completion()