# Jarvis 2.0: Consolidated LLM System Guide

This document explains the architecture and logic of the new unified LLM (Large Language Model) system in Jarvis 2.0.

---

## 1. 📂 File Structure
The system has been consolidated from 5+ files into three core modules:

*   **`assistant/core/llm_manager.py`**: The "Brain Orchestrator." It contains the logic to connect to Gemini, OpenRouter, HF, and others.
*   **`assistant/core/llm_utils.py`**: Shared utilities for cleaning text, splitting sentences for speech, and managing conversation history.
*   **`assistant/LLM/llm_search.py`**: A clean wrapper that provides backward compatibility for the rest of the app.

---

## 2. 🧠 Intelligent Intent Routing
To reduce latency and improve accuracy, the system analyzes your command first and routes it to the fastest model:

| Command Intent | Primary Model | Latency | Why? |
| :--- | :--- | :--- | :--- |
| **Technical/Coding** | **Gemini** | ~1.78s | High reasoning capability for debugging. |
| **Web/Current Events** | **GPT4Free (gpt-4o-mini)** | ~1.76s | Fastest model with integrated web-search. |
| **General Chat** | **GPT4Free (gpt-4o-mini)** | ~1.76s | Lowest latency for snappy responses. |

---

## 3. 🛡️ Cascading Fallback Chain
If the primary model fails, Jarvis automatically cycles through his "thinking modules" in order of speed:

1.  **GPT4Free** (1.76s)
2.  **Gemini** (1.78s)
3.  **HuggingFace** (2.39s)
4.  **OpenRouter** (2.91s)

---

## 4. ⚡ Performance Optimizations
*   **Lazy Loading**: Expensive modules are only imported when needed.
*   **Sentence Streaming**: Responses are split into sentences immediately so the voice engine can start speaking while the AI is still generating the rest of the answer.
*   **REST API Integration**: Uses direct HTTP calls for Gemini to avoid heavy SDK overhead.

---

## 5. 🛠️ How to Add a New Model
To add a new provider:
1.  Create a private method in `LLMManager` (e.g., `_call_new_api`).
2.  Add it to the `fallbacks` list in the `get_response` method in `llm_manager.py`.
3.  Add its API key to the `.env` file.
