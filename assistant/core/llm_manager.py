"""
LLM Manager Module - Intelligent Provider Orchestration

Consolidates multiple LLM providers (Gemini, Groq, OpenRouter, HF, g4f) into a 
single, high-performance asynchronous system. Features intelligent model selection based on 
query intent to minimize latency while maximizing response quality.
"""

import os
import aiohttp
import asyncio
import threading
from typing import List, Dict, Optional
from dotenv import load_dotenv
from assistant.core.llm_utils import clean_llm_output, split_sentences, trim_history, save_to_brain
from assistant.activities.activity_monitor import record_user_activity

load_dotenv()
import json

HISTORY_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "brain_data", "chat_history.json")

# Global conversation history
CHAT_HISTORY: List[Dict[str, str]] = []
HISTORY_LOCK = threading.Lock()

def load_history():
    global CHAT_HISTORY
    if os.path.exists(HISTORY_FILE_PATH):
        try:
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                CHAT_HISTORY = json.load(f)
                if not isinstance(CHAT_HISTORY, list):
                    CHAT_HISTORY = []
        except Exception as e:
            print(f"[LLM] Error loading chat history: {e}")
            CHAT_HISTORY = []

def save_history():
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE_PATH), exist_ok=True)
        with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(CHAT_HISTORY, f, indent=4)
    except Exception as e:
        print(f"[LLM] Error saving chat history: {e}")

load_history()

def add_to_history(user_text: str, assistant_text: str):
    """Allows other modules (like local brain) to inject interactions into LLM context."""
    global CHAT_HISTORY
    with HISTORY_LOCK:
        CHAT_HISTORY.append({"role": "user", "content": user_text})
        CHAT_HISTORY.append({"role": "assistant", "content": assistant_text})
        CHAT_HISTORY = trim_history(CHAT_HISTORY, max_messages=10)
        save_history()

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
    """
    Manages connections and failovers for multiple Large Language Models asynchronously.
    """
    def __init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")

    async def _call_gemini(self, messages: List[Dict[str, str]]) -> Optional[str]:
        if not self.gemini_key: return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={self.gemini_key}"
        
        contents = []
        for msg in messages:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
            
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=60) as response:
                    data = await response.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"[LLM] Gemini error: {e}")
            return None

    async def _call_huggingface(self, messages: List[Dict[str, str]]) -> Optional[str]:
        if not self.hf_token: return None
        def run_hf():
            from huggingface_hub import InferenceClient
            try:
                client = InferenceClient(token=self.hf_token)
                res = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    max_tokens=800
                )
                return res.choices[0].message.content
            except Exception as e:
                print(f"[LLM] HuggingFace error: {e}")
                return None
        return await asyncio.to_thread(run_hf)

    async def _call_openrouter(self, messages: List[Dict[str, str]], model: str = "openrouter/free") -> Optional[str]:
        if not self.openrouter_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openrouter_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "temperature": 0.7
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=60) as response:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"[LLM] OpenRouter error: {e}")
            return None

    async def _call_g4f(self, messages: List[Dict[str, str]]) -> Optional[str]:
        # g4f is generally synchronous, running in a thread to prevent blocking
        def run_g4f():
            from g4f.client import Client
            try:
                client = Client()
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    web_search=True
                )
                return response.choices[0].message.content
            except: return None
        return await asyncio.to_thread(run_g4f)

    def _identify_intent(self, text: str) -> str:
        text = text.lower()
        if any(kw in text for kw in ["python", "code", "bug", "error", "fix", "function", "write a", "program"]):
            return "technical"
        if any(kw in text for kw in ["news", "weather", "today", "current", "search for"]):
            return "web"
        return "general"

    async def get_response_async(self, user_input: str) -> str:
        record_user_activity()
        intent = self._identify_intent(user_input)
        res = None
        
        global CHAT_HISTORY
        with HISTORY_LOCK:
            CHAT_HISTORY.append({"role": "user", "content": user_input})
            CHAT_HISTORY = trim_history(CHAT_HISTORY, max_messages=10)
            save_history()
            messages_to_send = list(CHAT_HISTORY)

        if intent == "technical":
            print(f"[LLM] Technical query. Using HuggingFace (Primary)...")
            res = await self._call_huggingface(messages_to_send)
        elif intent == "web":
            print(f"[LLM] Web query. Using GPT4Free (Primary)...")
            res = await self._call_g4f(messages_to_send)
        else:
            print(f"[LLM] General query. Using Gemini (Primary)...")
            res = await self._call_gemini(messages_to_send)

        if not res:
            print("[LLM] Primary failed. Starting sequential fallback...")
            fallbacks = [
                self._call_gemini,
                self._call_huggingface,
                lambda msgs: self._call_openrouter(msgs, model="openai/gpt-oss-120b:free"),
                self._call_g4f
            ]
            for attempt in fallbacks:
                res = await attempt(messages_to_send)
                if res: break

        if not res:
            error_msg = "I am unable to reach any of my thinking modules at the moment. Please check your internet connection."
            from assistant.core.speak_selector import speak
            speak(error_msg)
            # Remove the failed user input from history
            with HISTORY_LOCK:
                if CHAT_HISTORY and CHAT_HISTORY[-1].get("role") == "user":
                    CHAT_HISTORY.pop()
                    save_history()
            return error_msg

        clean_text = clean_llm_output(res)
        
        # Save assistant response to history
        with HISTORY_LOCK:
            CHAT_HISTORY.append({"role": "assistant", "content": clean_text})
            save_history()
            
        await asyncio.to_thread(save_to_brain, user_input, clean_text)
        
        return clean_text

    def get_response_sync(self, user_input: str) -> str:
        """Synchronous wrapper for async get_response"""
        try:
            loop = asyncio.get_running_loop()
            # If we are already in an event loop, we can't block it with run_until_complete
            # We must use a thread to run the async function
            with threading.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(self.get_response_async(user_input))).result()
        except RuntimeError:
            return asyncio.run(self.get_response_async(user_input))

# Singleton instance
manager = LLMManager()

def llm_response(text: str) -> str:
    """Consolidated entry point for LLM responses."""
    return manager.get_response_sync(text)

def llm_response_streaming(text: str) -> List[str]:
    """Returns split sentences for streaming TTS and speaks them."""
    response = manager.get_response_sync(text)
    sentences = split_sentences(response)
    
    from assistant.core.speak_selector import speak_streaming
    from assistant.core.event_bus import bus, EventType
    import time
    
    speak_streaming(sentences)
    return sentences
