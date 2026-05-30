"""
Model Module - Local Q&A Intelligence System with TF-IDF and Cosine Similarity

This module implements a local, offline question-answering system using natural language
processing techniques. It provides fast, privacy-preserving responses by matching user
queries against a pre-existing Q&A dataset using TF-IDF vectorization and cosine similarity.
It also uses ChromaDB as a vector store for semantic similarity and RAG capabilities.

Key Features:
- Local offline Q&A without external API dependencies
- TF-IDF vectorization for semantic understanding
- Cosine similarity for intelligent question matching
- ChromaDB for semantic similarity and RAG (ingesting user documents)
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
- chromadb: Vector database for semantic search and RAG
"""

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
import chromadb
import joblib

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

from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# Global ChromaDB client
_chroma_client = None
_qna_collection = None
_docs_collection = None

def init_chroma(db_path: str):
    global _chroma_client, _qna_collection, _docs_collection
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=db_path)
        
        # Explicitly omit TensorrtExecutionProvider to suppress ugly ONNX warnings
        emb_fn = ONNXMiniLM_L6_V2(preferred_providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        
        try:
            _qna_collection = _chroma_client.get_or_create_collection(
                name="jarvis_qna",
                embedding_function=emb_fn
            )
        except ValueError:
            # If there's an embedding function conflict with an old version, recreate it
            _chroma_client.delete_collection("jarvis_qna")
            _qna_collection = _chroma_client.get_or_create_collection(
                name="jarvis_qna",
                embedding_function=emb_fn
            )
            
        try:
            _docs_collection = _chroma_client.get_or_create_collection(
                name="jarvis_docs",
                embedding_function=emb_fn
            )
        except ValueError:
            _chroma_client.delete_collection("jarvis_docs")
            _docs_collection = _chroma_client.get_or_create_collection(
                name="jarvis_docs",
                embedding_function=emb_fn
            )

def load_dataset(file_path: str) -> List[Dict[str, str]]:
    """
    Load and parse the Q&A dataset from a JSON file.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        qa_dict = json.load(file)
    dataset = [{"question": q, "answer": a} for q, a in qa_dict.items()]
    return dataset


# Cache NLP tools globally to avoid massive I/O overhead during dataset retraining
_stop_words = set(stopwords.words("english"))
_stemmer = PorterStemmer()

def preprocess_text(text: str) -> str:
    """
    Comprehensive text preprocessing pipeline for NLP tasks.
    """
    tokens = word_tokenize(text.lower())
    tokens = [
        _stemmer.stem(token)
        for token in tokens
        if token.isalnum()
        and token not in _stop_words
    ]
    return " ".join(tokens)


def train_tfidf_vectorizer(dataset: List[Dict[str, str]]) -> Tuple[TfidfVectorizer, Any]:
    """
    Train TF-IDF vectorizer on the Q&A dataset.
    """
    corpus = [preprocess_text(qa["question"]) for qa in dataset]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(corpus)
    return vectorizer, X


def get_answer(question: str, vectorizer: TfidfVectorizer, X: Any, dataset: List[Dict[str, str]], threshold: float = 0.5) -> Tuple[Optional[str], float]:
    """
    Find the best matching answer for a user question using cosine similarity.
    """
    processed_question = preprocess_text(question)
    question_vec = vectorizer.transform([processed_question])
    similarities = cosine_similarity(question_vec, X)
    
    best_match_index = similarities.argmax()
    best_similarity = similarities[0][best_match_index]

    if best_similarity > threshold:
        matched_q = dataset[best_match_index]['question']
        len_q = len(processed_question.split())
        len_m = len(preprocess_text(matched_q).split())
        
        # Protect against OOV collapse (where unknown words are stripped, leaving a 100% match on a single word)
        if len_q > 0 and len_m > 0:
            ratio = min(len_q, len_m) / max(len_q, len_m)
            if ratio >= 0.5:
                return dataset[best_match_index]["answer"], best_similarity
                
        # If ratio is too low, reject the false positive
        print(f"Rejected false positive due to length mismatch: '{matched_q}' (Ratio: {ratio:.2f})")
        return None, best_similarity
    else:
        return None, best_similarity


# --- Caching Mechanism ---
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

    if _cached_dataset is None or current_mtime > _last_mtime:
        _cached_dataset = load_dataset(dataset_path)
        
        cache_path = os.path.join(os.path.dirname(dataset_path), "tfidf_cache.joblib")
        try:
            cache_mtime = os.path.getmtime(cache_path)
        except OSError:
            cache_mtime = 0

        if cache_mtime >= current_mtime:
            print(f"Loading intelligence model from cache... (Source: {os.path.basename(cache_path)})")
            _cached_vectorizer, _cached_matrix = joblib.load(cache_path)
        else:
            print(f"Training intelligence model... (Source: {os.path.basename(dataset_path)})")
            _cached_vectorizer, _cached_matrix = train_tfidf_vectorizer(_cached_dataset)
            try:
                joblib.dump((_cached_vectorizer, _cached_matrix), cache_path)
            except Exception as e:
                print(f"Failed to save TF-IDF cache: {e}")

        _last_mtime = current_mtime
        
        # Differential Sync with ChromaDB to eliminate inference delay
        db_path = os.path.join(os.path.dirname(dataset_path), "chroma_db")
        init_chroma(db_path)
        
        import hashlib
        
        existing = _qna_collection.get(include=['metadatas'])
        existing_map = {}
        if existing and existing['ids']:
            for idx, _id in enumerate(existing['ids']):
                existing_map[_id] = existing['metadatas'][idx]['answer']
        
        valid_ids = set()
        docs_to_upsert = []
        metas_to_upsert = []
        ids_to_upsert = []
        
        for qa in _cached_dataset:
            q_text = qa["question"]
            a_text = qa["answer"]
            q_id = hashlib.md5(q_text.encode('utf-8')).hexdigest()
            valid_ids.add(q_id)
            
            # If it's new or the answer changed, we need to upsert
            if q_id not in existing_map or existing_map[q_id] != a_text:
                docs_to_upsert.append(q_text)
                metas_to_upsert.append({"answer": a_text})
                ids_to_upsert.append(q_id)
                
        # Delete items that are no longer in the JSON
        ids_to_delete = set(existing_map.keys()) - valid_ids
        if ids_to_delete:
            _qna_collection.delete(ids=list(ids_to_delete))
            
        # Upsert only the new/changed items (bypasses heavy ONNX embedding for unchanged items)
        if docs_to_upsert:
            try:
                _qna_collection.upsert(
                    documents=docs_to_upsert,
                    metadatas=metas_to_upsert,
                    ids=ids_to_upsert
                )
            except Exception as e:
                print(f"Failed to upsert to ChromaDB: {e}")


def ingest_document(file_path: str) -> None:
    """
    Ingest a user document (text/PDF) into ChromaDB for RAG.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(project_root, "data", "brain_data", "chroma_db")
    init_chroma(db_path)
    
    text = ""
    if file_path.endswith('.txt') or file_path.endswith('.md'):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    elif file_path.endswith('.pdf'):
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except ImportError:
            print("PyPDF2 is required for PDF ingestion. Please install it (`pip install PyPDF2`).")
            return
            
    if not text.strip():
        print("No text extracted.")
        return
        
    chunk_size = 200
    overlap = 50
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        
    documents = chunks
    metadatas = [{"source": os.path.basename(file_path)} for _ in chunks]
    ids = [f"{os.path.basename(file_path)}_{i}" for i in range(len(chunks))]
    
    try:
        _docs_collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully ingested {len(chunks)} chunks from {file_path} into ChromaDB.")
    except Exception as e:
        print(f"Failed to ingest document into ChromaDB: {e}")


def mind(text: str, threshold: float = 0.7) -> Optional[str]:
    """
    Main interface function for the local Q&A intelligence system.
    Orchestrates query processing using TF-IDF with ChromaDB semantic search as a fallback.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "data", "brain_data", "qna_data.json")

    ensure_model_loaded(dataset_path)

    answer, similarity = get_answer(text, _cached_vectorizer, _cached_matrix, _cached_dataset, threshold)
    print(f"TF-IDF Answer: {answer}, Similarity: {similarity}, Threshold: {threshold}")
    if answer and similarity > 0.85:
        # High confidence exact match from TF-IDF
        print("Returning TF-IDF exact match.")
        return answer
        
    # ChromaDB Semantic Similarity / RAG Fallback
    db_path = os.path.join(os.path.dirname(dataset_path), "chroma_db")
    init_chroma(db_path)
    
    best_answer = answer
    best_distance = float('inf')
    
    try:
        # Pre-compute the query embedding to cut the inference delay in half
        # Otherwise, query_texts=[text] runs the neural network twice!
        emb_fn = _qna_collection._embedding_function
        query_embedding = emb_fn([text])
        
        # Query QnA collection
        qna_results = _qna_collection.query(
            query_embeddings=query_embedding,
            n_results=1
        )
        
        if qna_results['distances'] and qna_results['distances'][0]:
            qna_dist = qna_results['distances'][0][0]
            # all-MiniLM-L6-v2 packs embeddings very tightly. 
            # Unrelated queries often have distances ~0.8. 
            # We need a very strict threshold (< 0.3) for QnA exact/near-exact matches.
            if qna_dist < 0.3:  
                best_distance = qna_dist
                best_answer = qna_results['metadatas'][0][0]['answer']
                
        # Query Docs collection (RAG)
        docs_results = _docs_collection.query(
            query_embeddings=query_embedding,
            n_results=1
        )
        
        if docs_results['distances'] and docs_results['distances'][0]:
            doc_dist = docs_results['distances'][0][0]
            # RAG chunks are longer, so distance is naturally higher than QnA pairs.
            if doc_dist < best_distance and doc_dist < 1.0:
                best_answer = docs_results['documents'][0][0]
                
    except Exception as e:
        # Fallback to TF-IDF answer if Chroma fails
        print(f"ChromaDB Query Error: {e}")
        
    # If even after ChromaDB we have no answer and similarity is very poor, return None
    if best_answer is None or (best_distance == float('inf') and similarity < 0.5):
        return None
        
    return best_answer


if __name__ == "__main__":
    while True:
        x = input()
        print(mind(x))
