import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
from pathlib import Path

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


def load_dataset(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        with open(file_path, "r", encoding="utf-8") as file:
            qa_dict = json.load(file)

    dataset = [{"question": q, "answer": a} for q, a in qa_dict.items()]
    return dataset


def preprocess_text(text):
    stop_words = set(stopwords.words("english"))
    ps = PorterStemmer()
    tokens = word_tokenize(text.lower())
    tokens = [
        ps.stem(token)
        for token in tokens
        if token.isalnum() and token not in stop_words
    ]
    return " ".join(tokens)


def train_tfidf_vectorizer(dataset):
    corpus = [preprocess_text(qa["question"]) for qa in dataset]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(corpus)
    return vectorizer, X


def get_answer(question, vectorizer, X, dataset, threshold=0.5):
    question = preprocess_text(question)
    question_vec = vectorizer.transform([question])
    similarities = cosine_similarity(question_vec, X)
    best_match_index = similarities.argmax()
    best_similarity = similarities[0][best_match_index]

    print(f"Best similarity score: {best_similarity}")

    if best_similarity > threshold:
        return dataset[best_match_index]["answer"], best_similarity
    else:
        return None, best_similarity


def mind(text, threshold=0.7):
    dataset_path = r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\brain_data\qna_data.json"
    dataset = load_dataset(dataset_path)

    vectorizer, X = train_tfidf_vectorizer(dataset)
    user_question = text
    answer, similarity = get_answer(user_question, vectorizer, X, dataset, threshold)

    print(f"Query: {text}, Answer: {answer}, Similarity: {similarity}")

    return answer


if __name__ == "__main__":
    while True:
        x = input()
        mind(x)
