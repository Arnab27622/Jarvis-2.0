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
from assistant.core.config import config
from assistant.core.logger import get_logger
from assistant.core.llm_utils import clean_llm_output, split_sentences, trim_history, save_to_brain
from assistant.activities.activity_monitor import record_user_activity
import json

logger = get_logger("LLM")

# --- Persistent Event Loop for Connection Pooling ---
_llm_loop = asyncio.new_event_loop()
_llm_thread = threading.Thread(target=_llm_loop.run_forever, daemon=True)
_llm_thread.start()

HISTORY_FILE_PATH = str(config.chat_history_path)

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
            logger.error("Error loading chat history: %s", e)
            CHAT_HISTORY = []
    else:
        CHAT_HISTORY = []
        save_history()

def save_history():
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE_PATH), exist_ok=True)
        with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(CHAT_HISTORY, f, indent=4)
    except Exception as e:
        logger.error("Error saving chat history: %s", e)

load_history()

def add_to_history(user_text: str, assistant_text: str):
    """Allows other modules (like local brain) to inject interactions into LLM context."""
    global CHAT_HISTORY
    with HISTORY_LOCK:
        CHAT_HISTORY.append({"role": "user", "content": user_text})
        CHAT_HISTORY.append({"role": "assistant", "content": assistant_text})
        CHAT_HISTORY = trim_history(CHAT_HISTORY, max_messages=config.llm_max_history)
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

import uuid
import re
from google import genai
from google.genai import types
from assistant.core.event_bus import bus, EventType
from assistant.core.mouth import tts_queue

class LLMManager:
    """
    Manages connections and failovers for multiple Large Language Models asynchronously.
    """
    def __init__(self) -> None:
        self.gemini_key = config.gemini_api_key
        self.openrouter_key = config.openrouter_api_key
        self.hf_token = config.hf_token
        self._session: Optional[aiohttp.ClientSession] = None
        self.gemini_client = None
        if self.gemini_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=config.llm_timeout)
            )
        return self._session

    async def _call_gemini_streaming(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Calls Gemini natively with token streaming and function calling."""
        if not self.gemini_client: return None
        
        def run_gemini():
            from assistant.core.tools import AVAILABLE_TOOLS
            
            # Convert simple history to google-genai Content objects
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
                )

            last_msg = contents.pop()
            
            # We use chat so it can maintain the session if needed, but we pass full history here
            chat = self.gemini_client.chats.create(
                model="gemini-3.1-flash-lite",
                history=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=config.llm_temperature
                )
            )

            full_text = ""
            current_sentence = ""
            message_id = str(uuid.uuid4())
            
            # Send the stream
            response = chat.send_message_stream(last_msg.parts[0].text)
            
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    current_sentence += chunk.text
                    
                    # Split into sentences dynamically and stream to TTS
                    # Use a regex that keeps the punctuation attached to the sentence
                    parts = re.split(r'(?<=[.!?])\s+', current_sentence)
                    
                    # If we found at least one complete sentence
                    if len(parts) > 1:
                        # Queue all complete sentences
                        for complete_sentence in parts[:-1]:
                            if complete_sentence.strip():
                                bus.emit(EventType.LLM_STREAMING, (complete_sentence.strip(), None, message_id))
                        # Keep the incomplete part in the buffer
                        current_sentence = parts[-1]
            
            # Flush the remaining buffer
            if current_sentence.strip():
                bus.emit(EventType.LLM_STREAMING, (current_sentence.strip(), None, message_id))

            return full_text

        try:
            return await asyncio.to_thread(run_gemini)
        except Exception as e:
            logger.error("Gemini stream error: %s", e)
            return None

    async def _call_gemini_tools(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Calls Gemini with tools natively using non-streaming to avoid SDK bugs with AFC."""
        if not self.gemini_client: return None
        
        def run_gemini():
            from assistant.core.tools import AVAILABLE_TOOLS
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
                )

            last_msg = contents.pop()
            
            chat = self.gemini_client.chats.create(
                model="gemini-3.1-flash-lite",
                history=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=AVAILABLE_TOOLS,
                    temperature=config.llm_temperature
                )
            )

            # Send message synchronously to allow Automatic Function Calling (AFC) to complete
            response = chat.send_message(last_msg.parts[0].text)
            
            full_text = response.text or ""
            
            # Immediately queue the full text for TTS
            if full_text:
                from assistant.core.llm_utils import split_sentences
                sentences = split_sentences(full_text)
                message_id = str(uuid.uuid4())
                for sentence in sentences:
                    bus.emit(EventType.LLM_STREAMING, (sentence, None, message_id))
                    
            return full_text

        try:
            return await asyncio.to_thread(run_gemini)
        except Exception as e:
            logger.error("Gemini tools error: %s", e)
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
                    max_tokens=config.llm_max_tokens
                )
                return res.choices[0].message.content
            except Exception as e:
                logger.error("HuggingFace error: %s", e)
                return None
        return await asyncio.to_thread(run_hf)

    async def _call_openrouter(self, messages: List[Dict[str, str]], model: str = "openrouter/free") -> Optional[str]:
        if not self.openrouter_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openrouter_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "temperature": config.llm_temperature
        }
        try:
            session = await self._get_session()
            async with session.post(url, headers=headers, json=payload) as response:
                data = await response.json()
                return data['choices'][0]['message']['content']
        except Exception as e:
            logger.error("OpenRouter error: %s", e)
            return None

    async def _call_g4f(self, messages: List[Dict[str, str]]) -> Optional[str]:
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
        tts_handled = False
        
        global CHAT_HISTORY
        with HISTORY_LOCK:
            CHAT_HISTORY.append({"role": "user", "content": user_input})
            CHAT_HISTORY = trim_history(CHAT_HISTORY, max_messages=config.llm_max_history)
            save_history()
            messages_to_send = list(CHAT_HISTORY)

        if intent == "technical":
            logger.info("Technical query. Using HuggingFace (Primary)...")
            res = await self._call_huggingface(messages_to_send)
        elif intent == "web":
            logger.info("Web query. Using Gemini with Tools (Primary)...")
            res = await self._call_gemini_tools(messages_to_send)
            if res: tts_handled = True
        else:
            logger.info("General query. Using Gemini Streaming (Primary)...")
            res = await self._call_gemini_streaming(messages_to_send)
            if res: tts_handled = True

        if not res:
            logger.warning("Primary failed. Starting sequential fallback...")
            fallbacks = [
                self._call_gemini_streaming,
                self._call_huggingface,
                lambda msgs: self._call_openrouter(msgs, model="openai/gpt-oss-120b:free"),
                self._call_g4f
            ]
            for attempt in fallbacks:
                res = await attempt(messages_to_send)
                if res:
                    if attempt == self._call_gemini_streaming:
                        tts_handled = True
                    break

        if not res:
            error_msg = "I am unable to reach any of my thinking modules at the moment. Please check your internet connection."
            from assistant.core.speak_selector import speak
            speak(error_msg)
            with HISTORY_LOCK:
                if CHAT_HISTORY and CHAT_HISTORY[-1].get("role") == "user":
                    CHAT_HISTORY.pop()
                    save_history()
            return error_msg

        clean_text = clean_llm_output(res)
        
        if not tts_handled:
            from assistant.core.speak_selector import speak_streaming
            from assistant.core.llm_utils import split_sentences
            speak_streaming(split_sentences(clean_text))
        
        with HISTORY_LOCK:
            CHAT_HISTORY.append({"role": "assistant", "content": clean_text})
            save_history()
            
        from assistant.core.llm_utils import save_to_brain
        await asyncio.to_thread(save_to_brain, user_input, clean_text)
        
        return clean_text

    def get_response_sync(self, user_input: str) -> str:
        """Synchronous wrapper for async get_response using a persistent background loop."""
        future = asyncio.run_coroutine_threadsafe(self.get_response_async(user_input), _llm_loop)
        return future.result()

# Singleton instance
manager = LLMManager()

def llm_response(text: str) -> str:
    """Consolidated entry point for LLM responses."""
    return manager.get_response_sync(text)

def llm_response_streaming(text: str) -> List[str]:
    """
    Returns split sentences.
    TTS Streaming is now handled NATIVELY inside _call_gemini_streaming!
    So this function simply waits for the response and returns it.
    """
    response = manager.get_response_sync(text)
    from assistant.core.llm_utils import split_sentences
    sentences = split_sentences(response)
    return sentences
