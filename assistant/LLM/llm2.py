# llm2.py (modified for streaming)
import sys
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from assistant.core.speak_selector import speak, speak_streaming
from assistant.activities.activity_monitor import record_user_activity
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)
import re

load_dotenv()

conversation = [
    {
        "role": "system",
        "content": "You are Jarvis, a helpful AI assistant for a programmer. Your creator is Arnab Dey. Arnab Dey is the only one to use you. Provide concise, accurate answers to questions. You answer questions, no matter how long, very quickly with low latency.",
    }
]


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

    # Normalize whitespace
    clean = clean.strip()
    import re

    clean = re.sub(r"\n{2,}", "\n\n", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean


def _extract_text_from_content(content) -> str:
    """Robustly extract a string from HuggingFace `message.content`"""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    pieces = []

    if isinstance(content, dict):
        for key in ("text", "content", "message", "value"):
            if key in content and isinstance(content[key], str):
                pieces.append(content[key])
        if "content" in content and isinstance(content["content"], (list, tuple)):
            pieces.append(_extract_text_from_content(content["content"]))

        if not pieces:
            try:
                for v in content.values():
                    if isinstance(v, str):
                        pieces.append(v)
                    elif isinstance(v, (list, tuple, dict)):
                        pieces.append(_extract_text_from_content(v))
            except Exception:
                pieces.append(str(content))
        return " ".join([p for p in pieces if p])

    if isinstance(content, (list, tuple)):
        for item in content:
            if item is None:
                continue
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                if "text" in item and isinstance(item["text"], str):
                    pieces.append(item["text"])
                elif "content" in item:
                    pieces.append(_extract_text_from_content(item["content"]))
                else:
                    for v in item.values():
                        if isinstance(v, str):
                            pieces.append(v)
                        elif isinstance(v, (list, tuple, dict)):
                            pieces.append(_extract_text_from_content(v))
            else:
                pieces.append(str(item))
        return " ".join([p for p in pieces if p])

    return str(content)


def split_into_sentences(text: str) -> list:
    """Split text into sentences for streaming"""
    # Simple sentence splitting - you can improve this with nltk if needed
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Add punctuation back
    sentences_with_punct = []
    for i, sentence in enumerate(sentences):
        if i < len(sentences) - 1:
            sentences_with_punct.append(sentence + ".")
        else:
            sentences_with_punct.append(sentence)

    return sentences_with_punct


def llm2(user_input):
    """Original non-streaming version"""
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
    speak(reply)

    with qa_lock:
        qa_dict[user_input] = reply
        save_qa_data(qa_file_path, qa_dict)

    return reply


def llm2_streaming(user_input):
    """Streaming version that yields sentences"""
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

    # Split into sentences for streaming
    sentences = split_into_sentences(reply)

    # Save to Q&A data
    with qa_lock:
        qa_dict[user_input] = reply
        save_qa_data(qa_file_path, qa_dict)

    return sentences


if __name__ == "__main__":
    while True:
        text = input("Enter your query: ")
        if text.strip() == "exit":
            print("Exiting...")
            sys.exit(0)
        else:
            # Use streaming version by default
            sentences = llm2_streaming(text)
            speak_streaming(sentences)
