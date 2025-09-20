import sys
import time
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from assistant.core.speak_selector import speak
from assistant.activities.activity_monitor import record_user_activity

load_dotenv()

conversation = [
    {
        "role": "system",
        "content": "You are Jarvis, a helpful AI assistant for a software engineer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
    }
]


def clean_output_parser(raw: str) -> str:
    """
    Clean the raw assistant output by:
    1. Converting Markdown to HTML.
    2. Parsing HTML to extract text (strip all tags).
    3. Optionally strip leftover Markdown if needed (for unusual cases).
    """

    if raw is None:
        return ""

    # 1) Convert Markdown to HTML
    # This handles bold, italics, links, etc.
    html = markdown.markdown(raw)

    # 2) Use BeautifulSoup to parse HTML and extract text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")  # separator ensures words don’t concatenate

    # 3) Optionally strip Markdown syntax (if any left over) using strip_markdown
    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        clean = text

    # 4) Normalize whitespace (collapse multiple spaces/newlines)
    # Remove leading/trailing whitespace
    clean = clean.strip()
    # Replace multiple newlines with at most one
    import re

    clean = re.sub(r"\n{2,}", "\n\n", clean)
    # Collapse many spaces
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean


def _extract_text_from_content(content) -> str:
    """
    Robustly extract a string from HuggingFace `message.content`, which can be:
      - a plain string
      - a list of chunks (each chunk can be str or dict)
      - a dict describing content
    The goal: return one sensible joined string.
    """
    if content is None:
        return ""

    # If it's already a string, use it
    if isinstance(content, str):
        return content

    pieces = []

    # If it's a dict that contains text-like fields, try to find them
    if isinstance(content, dict):
        # Common keys: "text", "content", "items" etc.
        for key in ("text", "content", "message", "value"):
            if key in content and isinstance(content[key], str):
                pieces.append(content[key])
        # Some providers nest a "content" as a list inside the dict
        if "content" in content and isinstance(content["content"], (list, tuple)):
            pieces.append(_extract_text_from_content(content["content"]))

        if not pieces:
            try:
                # Attempt to pull nested textual elements
                for v in content.values():
                    if isinstance(v, str):
                        pieces.append(v)
                    elif isinstance(v, (list, tuple, dict)):
                        pieces.append(_extract_text_from_content(v))
            except Exception:
                pieces.append(str(content))
        return " ".join([p for p in pieces if p])

    # If it's a list/tuple, walk items and extract recursively
    if isinstance(content, (list, tuple)):
        for item in content:
            if item is None:
                continue
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                # Some chunk dicts use keys like {"type":"text","text":"..."}
                if "text" in item and isinstance(item["text"], str):
                    pieces.append(item["text"])
                elif "content" in item:
                    pieces.append(_extract_text_from_content(item["content"]))
                else:
                    # Try to pull any string value
                    for v in item.values():
                        if isinstance(v, str):
                            pieces.append(v)
                        elif isinstance(v, (list, tuple, dict)):
                            pieces.append(_extract_text_from_content(v))
            else:
                # fallback: stringify (numbers etc.)
                pieces.append(str(item))
        return " ".join([p for p in pieces if p])

    # Fallback: stringify unknown types
    return str(content)


def llm2(user_input):
    """Generate response, then clean it using parser-based approach."""
    # Record user activity
    record_user_activity()

    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Set the HF_TOKEN environment variable to your Hugging Face API token."
        )
    conversation.append({"role": "user", "content": user_input})
    client = InferenceClient(token=token)
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b", messages=conversation, max_tokens=1500
    )
    raw_reply = response.choices[0].message.content
    raw_reply_str = _extract_text_from_content(raw_reply)
    reply = clean_output_parser(raw_reply_str)
    conversation.append({"role": "assistant", "content": reply})
    # speak(reply)


if __name__ == "__main__":
    while True:
        text = input("Enter your query: ")
        if text.strip() == "exit":
            print("Exiting...")
            sys.exit(0)
        else:
            llm2(text)
