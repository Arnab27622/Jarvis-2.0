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
    text = soup.get_text(separator=" ")  # separator ensures words don't concatenate

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


def generate(
    prompt: List[Dict[str, str]],
    system_prompt: str = "You are Jarvis, a helpful AI assistant for a software engineer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
    model: str = "Phind-70B",
    stream_chunk_size: int = 12,
    stream: bool = True,
) -> str:
    """
    Generates a response from the Phind-70B model based on the given prompt.

    Parameters:
    - prompt (List[Dict[str, str]]): The conversation history in a list of dictionaries format.
    - system_prompt (str, optional): The system prompt to use for the model.
    - model (str, optional): The model to use for generating the response.
    - stream_chunk_size (int, optional): The number of bytes to read from the response stream.
    - stream (bool, optional): Whether to stream the response. Defaults to True.

    Returns:
    - str: The generated text response from the model.
    """
    headers = {"User-Agent": ""}

    # Insert the system prompt at the beginning of the conversation history
    if system_prompt:
        if not prompt or prompt[0].get("role") != "system":
            prompt.insert(0, {"content": system_prompt, "role": "system"})
        else:
            prompt[0]["content"] = system_prompt

    payload = {
        "additional_extension_context": "",
        "allow_magic_buttons": True,
        "is_vscode_extension": True,
        "message_history": prompt,
        "requested_model": model,
        "user_input": prompt[-1]["content"],
    }

    # Send POST request and stream response
    chat_endpoint = "https://https.extension.phind.com/agent/"
    response = requests.post(chat_endpoint, headers=headers, json=payload, stream=True)

    # Collect streamed text content
    streaming_text = ""
    for value in response.iter_lines(decode_unicode=True, chunk_size=stream_chunk_size):
        modified_value = re.sub("data:", "", value)
        if modified_value:
            try:
                json_modified_value = json.loads(modified_value)
                if stream:
                    content = json_modified_value["choices"][0]["delta"]["content"]
                    streaming_text += content
            except:
                continue

    # Clean the output with markdown formatting
    clean_completion = clean_output_parser(streaming_text)

    # Append assistant reply to history for future context
    prompt.append({"role": "assistant", "content": clean_completion})

    return clean_completion


def llm4(text: str) -> str:
    """
    Simple text input function like llm3_text.
    Add the user's message to global history, trim it, call generate, and return the assistant's reply.

    Parameters:
    - text (str): The user input text string.

    Returns:
    - str: The assistant's response.
    """
    # Add user message to global history
    CHAT_HISTORY.append({"role": "user", "content": text})

    # Trim and summarize to keep context size manageable
    trimmed = trim_history(CHAT_HISTORY, max_messages=12)

    # Sync trimmed content back to the global list to avoid unbounded growth
    CHAT_HISTORY.clear()
    CHAT_HISTORY.extend(trimmed)

    # Call the model with current context
    res = generate(
        prompt=CHAT_HISTORY.copy(),  # Pass a copy to avoid modifying the original
        system_prompt="You are Jarvis, a helpful AI assistant for a software engineer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
        model="Phind-70B",
        stream=True,
    )

    speak(res)

    with qa_lock:
        qa_dict[text] = res
        save_qa_data(qa_file_path, qa_dict)


if __name__ == "__main__":
    while True:
        text_input = input("Enter your text: ")
        if text_input.strip().lower() in {"exit", "quit"}:
            break
        elif text_input.strip().lower() in {"clear", "reset"}:
            # Clear chat history
            CHAT_HISTORY.clear()
            print("Context cleared.")
            continue
        else:
            llm4(text_input)
