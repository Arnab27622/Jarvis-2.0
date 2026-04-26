"""
LLM Manager Module - Intelligent Provider Orchestration

Consolidates multiple LLM providers (Gemini, Groq, OpenRouter, HF, g4f) into a 
single, high-performance system. Features intelligent model selection based on 
query intent to minimize latency while maximizing response quality.
"""

import os
import requests
import threading
from typing import List, Dict, Optional
from dotenv import load_dotenv
from assistant.core.llm_utils import clean_llm_output, split_sentences, trim_history, save_to_brain
from assistant.activities.activity_monitor import record_user_activity

load_dotenv()

# Global conversation history
CHAT_HISTORY: List[Dict[str, str]] = []
HISTORY_LOCK = threading.Lock()

SYSTEM_PROMPT = (
    "You are JARVIS, a friendly, intelligent, and loyal digital companion for your creator, Arnab Dey. "
    "Your goal is to make Arnab's life easier and his coding sessions more productive. "
    "\n\nPersona & Guidelines:\n"
    "1. Tone: Warm, helpful, and professional. You aren't just an AI; you are Arnab's trusted assistant and friend.\n"
    "2. Efficiency: Keep your answers concise so they can be spoken quickly, but never sound robotic or cold.\n"
    "3. Support: Be encouraging. If Arnab is working on a difficult task, offer supportive and positive feedback.\n"
    "4. Exclusivity: You were built by Arnab, for Arnab. Always prioritize his needs and workflow.\n"
    "5. Style: When providing code, be precise but explain the 'why' in a friendly way."
)

class LLMManager:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Direct REST call to Gemini API (High Reliability, Good Speed)."""
        if not self.gemini_key: return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        except:
            return None

    def _call_openrouter(self, prompt: str, model: str = "openrouter/free") -> Optional[str]:
        """OpenRouter call (Fastest for Groq/Grok/Gemini Flash)."""
        if not self.openrouter_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openrouter_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            return response.json()['choices'][0]['message']['content']
        except:
            return None

    def _call_huggingface(self, prompt: str) -> Optional[str]:
        """LLM2 logic - GPT-OSS-20B."""
        if not self.hf_token: return None
        from huggingface_hub import InferenceClient
        try:
            client = InferenceClient(token=self.hf_token)
            # HF API often expects chat format or direct string
            res = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800
            )
            return res.choices[0].message.content
        except: return None

    def _call_g4f(self, prompt: str) -> Optional[str]:
        """LLM1 logic - GPT-4o-mini with Web Search."""
        from g4f.client import Client
        try:
            client = Client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                web_search=True
            )
            return response.choices[0].message.content
        except: return None

    def _identify_intent(self, text: str) -> str:
        """Determines if the query is Technical, Web-Search, or General."""
        text = text.lower()
        if any(kw in text for kw in ["python", "code", "bug", "error", "fix", "function", "write a", "program"]):
            return "technical"
        if any(kw in text for kw in ["news", "weather", "today", "current", "search for"]):
            return "web"
        return "general"

    def get_response(self, user_input: str) -> str:
        """
        Intelligent response generator using all available models.
        Selects best model by intent, then falls back through the entire chain.
        """
        record_user_activity()
        intent = self._identify_intent(user_input)
        res = None

        # --- 1. INTENT-BASED PRIMARY ATTEMPT (Based on Latency Tests) ---
        if intent == "technical":
            # Gemini is fastest for logic (1.78s)
            print(f"[LLM] Technical query. Using Gemini (Primary)...")
            res = self._call_gemini(user_input)
        elif intent == "web":
            # GPT4Free is fastest for web (1.76s)
            print(f"[LLM] Web query. Using GPT4Free (Primary)...")
            res = self._call_g4f(user_input)
        else:
            # GPT4Free is fastest overall (1.76s)
            print(f"[LLM] General query. Using GPT4Free (Primary)...")
            res = self._call_g4f(user_input)

        # --- 2. SEQUENTIAL FALLBACK CHAIN (Sorted by Speed) ---
        if not res:
            print("[LLM] Primary failed. Starting sequential fallback...")
            # Hierarchy: GPT4Free (1.76s) -> Gemini (1.78s) -> HF (2.39s) -> OpenRouter (2.91s)
            fallbacks = [
                lambda: self._call_g4f(user_input),
                lambda: self._call_gemini(user_input),
                lambda: self._call_huggingface(user_input),
                lambda: self._call_openrouter(user_input, model="openai/gpt-oss-120b:free")
            ]
            for attempt in fallbacks:
                res = attempt()
                if res: break

        if not res:
            return "I am unable to reach any of my thinking modules at the moment."

        # Clean and store
        clean_text = clean_llm_output(res)
        save_to_brain(user_input, clean_text)
        
        return clean_text

# Singleton instance
manager = LLMManager()

def llm_response(text: str) -> str:
    """Consolidated entry point for LLM responses."""
    return manager.get_response(text)

def llm_response_streaming(text: str) -> List[str]:
    """Returns split sentences for streaming TTS."""
    response = manager.get_response(text)
    return split_sentences(response)
