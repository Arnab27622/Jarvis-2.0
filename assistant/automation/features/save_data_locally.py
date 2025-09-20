import json
import os
from pathlib import Path
import tempfile
import threading


qa_lock = threading.Lock()


def load_qa_data(file_path):
    """Load Q&A data from JSON file for better structure"""
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
    """Save Q&A data to JSON file using atomic writing with temporary files"""
    try:
        file_path = Path(file_path)
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
                pass


# Use JSON format for better data structure
qa_file_path = (
    r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\brain_data\qna_data.json"
)
qa_dict = load_qa_data(qa_file_path)
