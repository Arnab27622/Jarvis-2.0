"""
Model Module - Local Q&A Intelligence System with TF-IDF and Cosine Similarity

This module implements a local, offline question-answering system using natural language
processing techniques. It provides fast, privacy-preserving responses by matching user
queries against a pre-existing Q&A dataset using TF-IDF vectorization and cosine similarity.

Key Features:
- Local offline Q&A without external API dependencies
- TF-IDF vectorization for semantic understanding
- Cosine similarity for intelligent question matching
- NLTK-based text preprocessing with stemming and stopword removal
- Configurable similarity threshold for response quality control
- Efficient in-memory model training and query processing

Architecture:
    User Query → Text Preprocessing → TF-IDF Vectorization →
    Cosine Similarity → Best Match Selection → Response

Dependencies:
- nltk: Natural Language Toolkit for text processing
- sklearn: Machine learning for TF-IDF and similarity calculations
- json: Dataset loading and management
"""

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import os

# Ensure required NLTK data packages are available
# Download necessary NLTK datasets if not already present
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")


from typing import List, Dict, Tuple, Optional, Any

def load_dataset(file_path: str) -> List[Dict[str, str]]:
    """
    Load and parse the Q&A dataset from a JSON file.

    Reads a JSON file containing question-answer pairs and converts it into
    a structured dataset format for processing. The JSON file should contain
    key-value pairs where keys are questions and values are answers.

    Args:
        file_path (str): Path to the JSON file containing Q&A data

    Returns:
        list: List of dictionaries with 'question' and 'answer' keys

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON

    Example:
        Input JSON: {"What is Python?": "A programming language", ...}
        Output: [{"question": "What is Python?", "answer": "A programming language"}, ...]
    """
    with open(file_path, "r", encoding="utf-8") as file:
        # Load Q&A pairs from JSON file (removed duplicate file opening)
        qa_dict = json.load(file)

    # Convert dictionary to list of question-answer pairs
    dataset = [{"question": q, "answer": a} for q, a in qa_dict.items()]
    return dataset


def preprocess_text(text: str) -> str:
    """
    Comprehensive text preprocessing pipeline for NLP tasks.

    Processes raw text through multiple normalization stages:
    1. Convert to lowercase for case insensitivity
    2. Tokenize into individual words
    3. Remove stopwords (common words with little semantic value)
    4. Apply Porter stemming to reduce words to their root forms
    5. Remove non-alphanumeric characters

    Args:
        text (str): Raw input text to preprocess

    Returns:
        str: Preprocessed and normalized text string

    Example:
        Input: "What is Python programming?"
        Output: "python program"
    """
    # Initialize NLP components
    stop_words = set(stopwords.words("english"))
    ps = PorterStemmer()

    # Convert to lowercase and tokenize into words
    tokens = word_tokenize(text.lower())

    # Filter and process tokens
    tokens = [
        ps.stem(token)  # Reduce to word stem
        for token in tokens
        if token.isalnum()
        and token not in stop_words  # Keep only alphanumeric, non-stopwords
    ]

    # Rejoin tokens into processed text string
    return " ".join(tokens)


def train_tfidf_vectorizer(dataset: List[Dict[str, str]]) -> Tuple[TfidfVectorizer, Any]:
    """
    Train TF-IDF vectorizer on the Q&A dataset.

    Creates and trains a Term Frequency-Inverse Document Frequency (TF-IDF)
    vectorizer on the preprocessed question corpus. This converts text questions
    into numerical vectors that capture their semantic importance.

    Args:
        dataset (list): List of Q&A dictionaries with 'question' keys

    Returns:
        tuple: (TfidfVectorizer, sparse matrix)
            - TfidfVectorizer: Fitted vectorizer for transforming new text
            - sparse matrix: TF-IDF matrix of the training questions

    Workflow:
        1. Extract and preprocess all questions from dataset
        2. Fit TF-IDF vectorizer on the processed corpus
        3. Transform questions into TF-IDF vectors
    """
    # Preprocess all questions in the dataset
    corpus = [preprocess_text(qa["question"]) for qa in dataset]

    # Initialize and train TF-IDF vectorizer
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(corpus)  # Transform corpus to TF-IDF matrix

    return vectorizer, X


def get_answer(question: str, vectorizer: TfidfVectorizer, X: Any, dataset: List[Dict[str, str]], threshold: float = 0.5) -> Tuple[Optional[str], float]:
    """
    Find the best matching answer for a user question using cosine similarity.

    Processes the user's question and compares it against all questions in the
    dataset using cosine similarity of TF-IDF vectors. Returns the best matching
    answer if similarity exceeds the threshold.

    Args:
        question (str): User's input question
        vectorizer (TfidfVectorizer): Pre-trained TF-IDF vectorizer
        X (sparse matrix): TF-IDF matrix of training questions
        dataset (list): Original Q&A dataset
        threshold (float): Minimum similarity score to return an answer (0.0-1.0)

    Returns:
        tuple: (answer, similarity_score)
            - answer (str or None): Best matching answer or None if below threshold
            - similarity_score (float): Cosine similarity of the best match

    Process:
        1. Preprocess user question
        2. Transform to TF-IDF vector
        3. Calculate cosine similarity with all dataset questions
        4. Find best match and check against threshold
    """
    # Preprocess the user question
    processed_question = preprocess_text(question)

    # Transform to TF-IDF vector
    question_vec = vectorizer.transform([processed_question])

    # Calculate cosine similarity with all dataset questions
    similarities = cosine_similarity(question_vec, X)

    # Find the best matching question index and similarity score
    best_match_index = similarities.argmax()
    best_similarity = similarities[0][best_match_index]

    # Debug output for similarity scoring
    print(f"Best similarity score: {best_similarity}")

    # Return answer if similarity exceeds threshold
    if best_similarity > threshold:
        return dataset[best_match_index]["answer"], best_similarity
    else:
        return None, best_similarity


# --- Caching Mechanism ---
# These variables store the trained model in memory to avoid redundant processing
_cached_dataset = None
_cached_vectorizer = None
_cached_matrix = None
_last_mtime = 0

def ensure_model_loaded(dataset_path: str) -> None:
    """
    Ensure the Q&A model is loaded and up-to-date.
    Uses a caching mechanism to avoid redundant training.
    """
    global _cached_dataset, _cached_vectorizer, _cached_matrix, _last_mtime

    try:
        current_mtime = os.path.getmtime(dataset_path)
    except OSError:
        current_mtime = 0

    # Re-train only if model is not loaded OR dataset file has changed
    if _cached_dataset is None or current_mtime > _last_mtime:
        print(f"Training intelligence model... (Source: {os.path.basename(dataset_path)})")
        _cached_dataset = load_dataset(dataset_path)
        _cached_vectorizer, _cached_matrix = train_tfidf_vectorizer(_cached_dataset)
        _last_mtime = current_mtime


def mind(text: str, threshold: float = 0.7) -> Optional[str]:
    """
    Main interface function for the local Q&A intelligence system.
    Orchestrates query processing using cached TF-IDF models.
    """
    # Calculate dataset path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "data", "brain_data", "qna_data.json")

    # Ensure the latest version of the model is in memory
    ensure_model_loaded(dataset_path)

    # Process user question and retrieve best answer
    answer, similarity = get_answer(text, _cached_vectorizer, _cached_matrix, _cached_dataset, threshold)

    return answer


if __name__ == "__main__":
    """
    Interactive testing interface for the local Q&A system.

    Provides a command-line interface for testing the mind function
    with direct user input. Useful for development and debugging.

    Usage:
        python model.py
        [Enter question]
        [View similarity score and response]
    """
    while True:
        x = input()
        mind(x)
