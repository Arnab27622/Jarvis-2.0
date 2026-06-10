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
    "5. Style: When providing code, be precise but explain the 'why' in a friendly way.\n"
    "6. RAG Context: If context is provided to you, synthesize it and answer the user's question concisely in your own words. Never read out large raw lists or regurgitate the context verbatim."
)

import uuid
import re
from assistant.core.event_bus import bus, EventType

class LLMManager:
    """
    Acts as the Router Agent, delegating tasks to Specialized Agents.
    Agents are imported lazily inside __init__ to avoid circular imports.
    """
    def __init__(self) -> None:
        # Lazy imports to break the circular dependency chain:
        # llm_manager → researcher → tools → wiki_search → llm_search → llm_manager
        from assistant.agents.base import BaseAgent
        from assistant.agents.researcher import ResearcherAgent
        from assistant.agents.coder import CoderAgent
        from assistant.agents.vision_agent import VisionAgent
        
        self.researcher = ResearcherAgent()
        self.coder = CoderAgent()
        self.vision = VisionAgent()
        
        # General Agent for basic conversation
        self.general = BaseAgent(
            name="Jarvis", 
            system_prompt=SYSTEM_PROMPT
        )

    def _identify_intent(self, text: str) -> str:
        text = text.lower()
        import re
        
        def has_kw(kws):
            pattern = r'\b(?:' + '|'.join(map(re.escape, kws)) + r')\b'
            return bool(re.search(pattern, text))
            
        if has_kw(["my screen", "screen", "look at this", "see this", "what is this", "what's on", "look", "see", "vision", "image", "picture"]):
            return "vision"
        if has_kw(["python", "code", "bug", "error", "fix", "function", "write a", "program", "script", "terminal"]):
            return "technical"
        if has_kw(["news", "weather", "today", "current", "search for", "find out", "research"]):
            return "web"
            
        return "general"

    async def get_response_async(self, user_input: str) -> str:
        record_user_activity()
        intent = self._identify_intent(user_input)
        res = None
        
        global CHAT_HISTORY
        with HISTORY_LOCK:
            CHAT_HISTORY.append({"role": "user", "content": user_input})
            CHAT_HISTORY = trim_history(CHAT_HISTORY, max_messages=config.llm_max_history)
            save_history()
            
            import copy
            import datetime
            messages_to_send = copy.deepcopy(CHAT_HISTORY)
            current_time = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
            
            # Fetch RAG Context
            from assistant.LLM.model import mind
            rag_context = mind(user_input, threshold=0.5, return_rag=True)
            
            context_string = ""
            if rag_context:
                context_string = (
                    f"\n\n--- BEGIN RETRIEVED MEMORY CONTEXT ---\n"
                    f"{rag_context}\n"
                    f"--- END RETRIEVED MEMORY CONTEXT ---\n"
                    f"CRITICAL INSTRUCTION: Use ONLY the memory context above to answer the user's question. "
                    f"Answer as briefly and naturally as possible."
                    f"DO NOT read or list out the entire context verbatim. If the answer is a single item, just say that item.\n\n"
                )
                
                # Clear chat history (except system msg) to prevent hallucination from previous RAG answers
                sys_msg = messages_to_send[0] if messages_to_send and messages_to_send[0].get("role") == "system" else None
                last_msg = messages_to_send[-1]
                messages_to_send = [sys_msg, last_msg] if sys_msg else [last_msg]

            messages_to_send[-1]["content"] = f"[System Time: {current_time}]{context_string}User Question: {user_input}"

        if intent == "vision":
            logger.info("ROUTING -> VisionAgent")
            res = await self.vision.run(messages_to_send, stream=True)
        elif intent == "technical":
            logger.info("ROUTING -> CoderAgent")
            # The coder has tools, so it might not stream cleanly yet
            res = await self.coder.run(messages_to_send, stream=False)
            if res:
                # Manually stream if it didn't stream automatically
                from assistant.core.llm_utils import split_sentences
                sentences = split_sentences(res)
                message_id = str(uuid.uuid4())
                for sentence in sentences:
                    bus.emit(EventType.LLM_STREAMING, (sentence, None, message_id))
        elif intent == "web":
            logger.info("ROUTING -> ResearcherAgent")
            res = await self.researcher.run(messages_to_send, stream=False)
            if res:
                from assistant.core.llm_utils import split_sentences
                sentences = split_sentences(res)
                message_id = str(uuid.uuid4())
                for sentence in sentences:
                    bus.emit(EventType.LLM_STREAMING, (sentence, None, message_id))
        else:
            logger.info("ROUTING -> GeneralAgent (Direct)")
            res = await self.general.run(messages_to_send, stream=True)
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
    TTS Streaming is now handled NATIVELY inside the agents!
    So this function simply waits for the response and returns it.
    """
    response = manager.get_response_sync(text)
    from assistant.core.llm_utils import split_sentences
    sentences = split_sentences(response)
    return sentences
