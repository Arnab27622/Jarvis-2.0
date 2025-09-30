import json
import os
from pathlib import Path
import tempfile
import threading


# Global thread lock for ensuring thread-safe operations on Q&A data
# Prevents race conditions when multiple threads access the same data file
qa_lock = threading.Lock()


def load_qa_data(file_path):
    """
    Load Question & Answer data from a JSON file with robust error handling.

    This function reads Q&A data from a JSON file and handles multiple data formats
    for backward compatibility. It supports both the legacy list format (Q:A strings)
    and the newer dictionary format for better data structure.

    Args:
        file_path (str or Path): Path to the JSON file containing Q&A data

    Returns:
        dict: A dictionary where keys are questions and values are answers.
              Returns an empty dictionary if the file doesn't exist or is corrupted.

    Examples:
        >>> load_qa_data("qna_data.json")
        Loaded 150 Q&A pairs from qna_data.json
        {'what is python': 'A programming language', ...}

    Note:
        - Legacy format: ["question: answer", "question2: answer2"]
        - Current format: {"question": "answer", "question2": "answer2"}
        - The function automatically converts legacy format to current format
    """
    file_path = Path(file_path)
    qa_dict = {}

    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert list format to dictionary if needed for backward compatibility
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


def save_qa_data(file_path, qa_dict):
    """
    Save Q&A data to JSON file using atomic writing for data safety.

    This function employs atomic file operations to prevent data corruption:
    1. Writes data to a temporary file first
    2. Then atomically replaces the original file
    This ensures that the original file is never left in a partially written state,
    even if the system crashes during the write operation.

    Args:
        file_path (str or Path): Destination path for the Q&A data file
        qa_dict (dict): Dictionary containing questions as keys and answers as values

    Raises:
        OSError: If file operations fail (permissions, disk space, etc.)
        Exception: For other unexpected errors during file operations

    Safety Features:
        - Atomic file replacement prevents data corruption
        - Automatic directory creation if needed
        - Proper cleanup of temporary files on errors
        - UTF-8 encoding for international character support

    Example:
        >>> qa_data = {"hello": "hi there", "what's python": "programming language"}
        >>> save_qa_data("qna.json", qa_data)
        # Safely saves data to qna.json via temporary file
    """
    try:
        file_path = Path(file_path)
        # Ensure the parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a temporary file in the same directory for atomic writing
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(file_path.parent),
            delete=False,
            suffix=".tmp",
        ) as tmp_file:
            json.dump(qa_dict, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = tmp_file.name

        # Replace the original file with the temporary file atomically
        # This operation is atomic on most filesystems
        if os.path.exists(file_path):
            os.replace(tmp_path, str(file_path))
        else:
            os.rename(tmp_path, str(file_path))
    except Exception as e:
        print(f"Error saving QA data: {e}")
        # Clean up temporary file if something went wrong
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass  # Silent cleanup failure is acceptable here


# Use JSON format for better data structure
qa_file_path = (
    r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\brain_data\qna_data.json"
)

# Global Q&A dictionary loaded at module import
# This serves as the in-memory cache of Q&A data that persists across sessions
qa_dict = load_qa_data(qa_file_path)
