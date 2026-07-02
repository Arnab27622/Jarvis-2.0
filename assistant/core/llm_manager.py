"""
LLM Manager Module - Intelligent Provider Orchestration

Consolidates multiple LLM providers (Gemini, Groq, OpenRouter, HF, g4f) into a 
single, high-performance asynchronous system. Features intelligent model selection based on 
query intent to minimize latency while maximizing response quality.
"""

import os
import asyncio
import threading
from typing import List, Dict
from assistant.core.config import config
from assistant.core.logger import get_logger
from assistant.core.llm_utils import clean_llm_output, split_sentences, trim_history, save_to_brain
from assistant.activities.activity_monitor import record_user_activity
import json
import uuid
import re
from assistant.core.event_bus import bus, EventType

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
        from assistant.core.tools import AVAILABLE_TOOLS
        
        self.researcher = ResearcherAgent()
        self.coder = CoderAgent()
        self.vision = VisionAgent()
        
        # General Agent for basic conversation
        self.general = BaseAgent(
            name="Jarvis", 
            system_prompt=SYSTEM_PROMPT
        )
        
        self.tool_agent = BaseAgent(
            name="ToolManager",
            system_prompt=(
                "You are Jarvis, Arnab's trusted assistant. Your primary function right now is to execute "
                "tools to help him with his request (like managing memory, setting reminders, reading emails, "
                "or interacting with the system). Act friendly, execute the tool, and answer Arnab's question "
                "naturally based on the tool output. If the user asks a yes/no question (such as 'is my battery low?'), "
                "make sure to answer it directly and naturally (for example: 'No, Arnab, your battery is at 100% and is plugged in').\n"
                "Capabilities you possess via tools:\n"
                "- Weather (use location='current' unless user specifies a city like 'Tokyo')\n"
                "- Image Generation\n"
                "- Alarms & Reminders\n"
                "- Terminal & Code Execution\n"
                "- File Management\n"
                "- YouTube (Always call search first, wait for results, then call play if needed. Do NOT call both simultaneously.)\n"
                "- System controls (brightness, volume, battery, memory, screenshot)\n"
                "CRITICAL INSTRUCTION: When you run a command or script on the user's system (e.g. powershell or python), "
                "ALWAYS output the exact command or script in a markdown block in your final text response so the user can see what was executed and it is saved in the chat history."
            ),
            tools=AVAILABLE_TOOLS
        )

    def _identify_intent(self, text: str) -> str:
        text = text.lower()
        
        def has_kw(kws):
            pattern = r'\b(?:' + '|'.join(map(re.escape, kws)) + r')\b'
            return bool(re.search(pattern, text))
            
        if has_kw(["my screen", "screen", "look at this", "see this", "what is this", "what's on", "look", "see", "vision"]):
            return "vision"
        if has_kw(["python", "code", "bug", "error", "fix", "function", "write a", "program", "script", "terminal"]):
            return "technical"
        if has_kw([
            "remind", "alarm", "timer", "remember", "memory", "youtube", "play", 
            "email", "system", "screenshot", "volume", "brightness", "image", "location",
            "playlist", "music", "song", "inbox", "gmail", "mail", "emails", 
            "battery", "power", "charge", "mind", "forget", "where am i", 
            "current city", "stretch", "take a break", "break", "wifi", "password",
            "file", "workspace", "directory", "folder", "read", "edit"
        ]):
            return "tools"
        if has_kw(["news", "weather", "today", "current", "search for", "find out", "research"]):
            return "web"
            
        return "general"

    def _build_messages_with_context(self, intent: str, user_input: str, chat_history: list[dict[str, str]]) -> list[dict[str, str]]:
        import copy
        import datetime
        messages_to_send = copy.deepcopy(chat_history)
        current_time = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        
        # Fetch RAG Context (ChromaDB docs) - ONLY for general intent!
        rag_context = ""
        if intent == "general":
            from assistant.LLM.model import mind
            rag_context = mind(user_input, threshold=0.5, return_rag=True)
        
        # Fetch remembered facts (always available as helper context)
        from assistant.automation.integrations.task_schedule_automation import _load_remembered_info
        remembered = _load_remembered_info()
        remembered_str = ""
        if remembered:
            remembered_items = []
            for k, v in remembered.items():
                clean_key = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}_', '', k)
                remembered_items.append(f"- {clean_key}: {v}")
            remembered_str = "Personal Facts/Memories:\n" + "\n".join(remembered_items)

        context_string = ""
        if intent == "general" and (remembered_str or rag_context):
            # For general conversation, we provide combined context and restrict the model to it.
            # In this case we clear the chat history (except system and last msg) to focus the model.
            combined_context = ""
            if remembered_str:
                combined_context += remembered_str + "\n\n"
            if rag_context:
                combined_context += "Document Context:\n" + rag_context
                
            context_string = (
                f"\n\n--- BEGIN RETRIEVED MEMORY CONTEXT ---\n"
                f"{combined_context}\n"
                f"--- END RETRIEVED MEMORY CONTEXT ---\n"
                f"CRITICAL INSTRUCTION: If the user is asking about personal facts or memories, use the context above to answer. "
                f"Otherwise, ignore the memory context and continue the conversation naturally based on the chat history. "
                f"DO NOT read or list out the entire context verbatim. Answer as briefly and naturally as possible.\n\n"
            )
        elif remembered_str:
            # For specialized tool/web/code agents, we inject the remembered facts as simple background info
            # WITHOUT clearing history, and WITHOUT the strict RAG instruction, so they can still use their tools!
            context_string = (
                f"\n\n--- USER INFORMATION & MEMORIES ---\n"
                f"{remembered_str}\n"
                f"------------------------------------\n\n"
            )

        messages_to_send[-1]["content"] = f"[System Time: {current_time}]{context_string}User Question: {user_input}"
        return messages_to_send

    async def get_response_async(self, user_input: str) -> str:
        record_user_activity()
        intent = self._identify_intent(user_input)
        res = None
        
        global CHAT_HISTORY
        with HISTORY_LOCK:
            CHAT_HISTORY.append({"role": "user", "content": user_input})
            CHAT_HISTORY = trim_history(CHAT_HISTORY, max_messages=config.llm_max_history)
            save_history()
            
            messages_to_send = self._build_messages_with_context(intent, user_input, CHAT_HISTORY)


        if intent == "vision":
            logger.info("ROUTING -> VisionAgent")
            res = await self.vision.run(messages_to_send, stream=True)
        elif intent == "technical":
            logger.info("ROUTING -> CoderAgent")
            # The coder has tools, so it might not stream cleanly yet
            res = await self.coder.run(messages_to_send, stream=False)
            if res:
                # Manually stream if it didn't stream automatically
                sentences = split_sentences(res)
                message_id = str(uuid.uuid4())
                for sentence in sentences:
                    bus.emit(EventType.LLM_STREAMING, (sentence, None, message_id))
        elif intent == "web":
            logger.info("ROUTING -> ResearcherAgent")
            res = await self.researcher.run(messages_to_send, stream=False)
            if res:
                sentences = split_sentences(res)
                message_id = str(uuid.uuid4())
                for sentence in sentences:
                    bus.emit(EventType.LLM_STREAMING, (sentence, None, message_id))
        elif intent == "tools":
            logger.info("ROUTING -> ToolAgent")
            res = await self.tool_agent.run(messages_to_send, stream=False)
            if res:
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
    sentences = split_sentences(response)
    return sentences
