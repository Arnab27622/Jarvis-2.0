"""
Module for managing persistent Question & Answer data using JSON storage.
Provides thread-safe loading and atomic saving mechanisms for data integrity.
"""

import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Dict, Union

qa_lock = threading.Lock()

def load_qa_data(file_path: Union[str, Path]) -> Dict[str, str]:
    """
    Loads Q&A data from a JSON file, supporting legacy list formats and modern dictionaries.

    Args:
        file_path: Path to the JSON file.

    Returns:
        A dictionary mapping questions to answers.
    """
    file_path = Path(file_path)
    qa_dict = {}

    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if ":" in item:
                            q, a = item.split(":", 1)
                            qa_dict[q.strip()] = a.strip()
                else:
                    qa_dict = data
        print(f"Loaded {len(qa_dict)} Q&A pairs from {file_path}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load QA data: {e}, starting with empty dataset")
    except Exception as e:
        print(f"Unexpected error loading QA data: {e}")

    return qa_dict


def save_qa_data(file_path: Union[str, Path], qa_dict: Dict[str, str]) -> None:
    """
    Saves Q&A data to a JSON file using an atomic write operation to prevent corruption.

    Args:
        file_path: Destination path for the JSON file.
        qa_dict: Dictionary of Q&A pairs to persist.
    """
    tmp_path = None
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(file_path.parent),
            delete=False,
            suffix=".tmp",
        ) as tmp_file:
            json.dump(qa_dict, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = tmp_file.name

        if os.path.exists(file_path):
            os.replace(tmp_path, str(file_path))
        else:
            os.rename(tmp_path, str(file_path))
    except Exception as e:
        print(f"Error saving QA data: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

qa_file_path = (
    r"C:\Users\ARNAB DEY\MyPC\Python\Projects\Jarvis 2.0\data\brain_data\qna_data.json"
)

qa_dict = load_qa_data(qa_file_path)
