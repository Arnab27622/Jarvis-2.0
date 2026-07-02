import asyncio
from typing import List, Dict, Optional, Any
from assistant.core.config import config
from assistant.core.logger import get_logger

logger = get_logger("BaseAgent")

class BaseAgent:
    """
    Base class for all specialized sub-agents.
    Each agent gets its own system prompt and optional tool set.
    """
    def __init__(self, name: str, system_prompt: str, tools: Optional[List[Any]] = None, model_name: str = "gemini-3.1-flash-lite"):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model_name = model_name
        
        # Default to configured model for extreme speed and low latency
        self.api_key = config.gemini_api_key
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"[{self.name}] Failed to initialize Gemini client: {e}")

    async def run(self, messages: List[Dict[str, str]], stream: bool = False) -> Optional[str]:
        """
        Executes the agent's logic. Calls Gemini with the agent's system prompt and tools.
        Runs the synchronous Gemini SDK in a background thread to avoid blocking the event loop.
        """
        if not self.client:
            logger.error(f"[{self.name}] Client not initialized.")
            return None

        def _execute():
            from google.genai import types
            contents = []
            
            # Transform OpenAI-style message history into Gemini Content parts
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
                )

            last_msg = contents.pop()

            chat = self.client.chats.create(
                model=self.model_name,
                history=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    tools=self.tools if self.tools else None,
                    temperature=config.llm_temperature
                )
            )

            if stream and not self.tools:
                # Natively stream directly to the event bus for low-latency TTS
                from assistant.core.event_bus import bus, EventType
                import re
                import uuid
                
                response = chat.send_message_stream(last_msg.parts[0].text)
                
                full_text = ""
                current_sentence = ""
                message_id = str(uuid.uuid4())
                
                for chunk in response:
                    if chunk.text:
                        full_text += chunk.text
                        current_sentence += chunk.text
                        
                        # If we are inside a markdown code block, DO NOT split into sentences.
                        # This allows the entire code block to be emitted at once, 
                        # so the TTS regex can filter it out completely.
                        in_code_block = current_sentence.count("```") % 2 != 0
                        
                        if not in_code_block:
                            # If we just closed a code block, emit it immediately
                            if "```" in current_sentence:
                                bus.emit(EventType.LLM_STREAMING, (current_sentence.strip(), None, message_id))
                                current_sentence = ""
                            else:
                                parts = re.split(r'(?<=[.!?])\s+', current_sentence)
                                if len(parts) > 1:
                                    for complete_sentence in parts[:-1]:
                                        if complete_sentence.strip():
                                            bus.emit(EventType.LLM_STREAMING, (complete_sentence.strip(), None, message_id))
                                    current_sentence = parts[-1]
                            
                if current_sentence.strip():
                    bus.emit(EventType.LLM_STREAMING, (current_sentence.strip(), None, message_id))
                    
                return full_text
            else:
                # Synchronous call (needed when using Tools / AFC)
                import assistant.core.mouth as mouth
                try:
                    mouth.mute_speak = True
                    response = chat.send_message(last_msg.parts[0].text)
                finally:
                    mouth.mute_speak = False
                return response.text or ""

        try:
            logger.info(f"[{self.name}] Agent executing query...")
            return await asyncio.to_thread(_execute)
        except Exception as e:
            logger.error(f"[{self.name}] Error during execution: {e}")
            return None
