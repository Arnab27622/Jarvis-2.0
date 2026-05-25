"""
LLM Utilities Module - Shared Text Processing and Context Management

Provides centralized utilities for LLM response cleaning, sentence segmentation,
conversation history management, and persistent Q&A storage.
"""

import re
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from typing import List, Dict
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)

def clean_llm_output(raw_text: str) -> str:
    """
    Unified cleaning pipeline for LLM outputs.
    Removes markdown, HTML, and normalizes whitespace/Unicode.
    """
    if not raw_text:
        return ""

    # 1. Convert Markdown to HTML then strip tags (robust approach)
    html = markdown.markdown(raw_text)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")

    # 2. Strip remaining markdown syntax
    try:
        clean = strip_markdown.strip_markdown(text)
    except:
        clean = text

    # 3. Unicode normalization
    replacements = {
        "â": "'", "ð": "", "â€œ": '"', "â€ ": '"', "â€˜": "'",
        "â€™": "'", "â€¦": "...", "â€¢": "-", "â€”": "--", "â€“": "-"
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)

    # 4. Remove non-printable characters
    clean = re.sub(r"[^\x20-\x7E\u00A0-\u00FF\u2013\u2014\u2018\u2019\u201C\u201D]", "", clean)

    # 5. Remove promotional ads (specifically g4f/op.wtf)
    ad_patterns = [
        r"Need proxies cheaper than the market\?https://op\.wtf.*",
        r"Give us a star on GitHub.*",
        r"Enjoying g4f\?.*"
    ]
    for pattern in ad_patterns:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)

    # 6. Strip LaTeX commands and symbols that TTS struggles with
    clean = clean.replace('$', '')
    clean = re.sub(r'\\text\{([^}]*)\}', r'\1', clean)
    clean = clean.replace(r'\times', 'times')
    clean = clean.replace(r'\div', 'divided by')
    clean = clean.replace(r'\pm', 'plus or minus')
    clean = clean.replace(r'\approx', 'approximately')
    clean = clean.replace(r'\neq', 'not equal to')
    clean = clean.replace(r'\leq', 'less than or equal to')
    clean = clean.replace(r'\geq', 'greater than or equal to')
    clean = clean.replace(r'\rightarrow', 'implies')
    clean = clean.replace(r'\leftarrow', 'is implied by')
    clean = clean.replace(r'\infty', 'infinity')
    clean = clean.replace('\\', ' ')
    clean = clean.replace('*', '')
    clean = clean.replace('`', '')
    clean = clean.replace('_', ' ')
    clean = clean.replace('#', '')

    # 7. Normalize whitespace
    clean = clean.strip()
    clean = re.sub(r"\n{2,}", "\n\n", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean

def split_sentences(text: str) -> List[str]:
    """Splits text into clean sentences for streaming TTS playback."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 2]

def trim_history(history: List[Dict[str, str]], max_messages: int = 10) -> List[Dict[str, str]]:
    """Manages conversation context size while preserving the system prompt."""
    if not history:
        return []
    
    sys_msg = history[0] if history[0].get("role") == "system" else None
    content_msgs = history[1:] if sys_msg else history
    
    if len(content_msgs) > max_messages:
        content_msgs = content_msgs[-max_messages:]
        
    return ([sys_msg] if sys_msg else []) + content_msgs

def save_to_brain(query: str, answer: str) -> None:
    """Stores successful Q&A pair in the local intelligence database."""
    with qa_lock:
        qa_dict[query] = answer
        save_qa_data(qa_file_path, qa_dict)
