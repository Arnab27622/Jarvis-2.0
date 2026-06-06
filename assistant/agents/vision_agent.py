from assistant.agents.base import BaseAgent
from assistant.core.logger import get_logger
import asyncio

logger = get_logger("VisionAgent")

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Vision",
            system_prompt="You are the Vision Agent. You specialize in analyzing screenshots of the user's screen."
        )

    async def run(self, messages: list, stream: bool = False) -> str:
        if not self.client: return "Vision system offline."
        
        def run_vision():
            from assistant.core.vision import capture_screen
            from google.genai import types
            
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
                )
            
            last_msg = contents.pop()
            
            chat = self.client.chats.create(
                model="gemini-3.1-flash-lite",
                history=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.3
                )
            )
            
            img = capture_screen()
            if not img:
                return chat.send_message(last_msg.parts[0].text + " (Note: I couldn't capture the screen.)").text
            else:
                response = chat.send_message([img, last_msg.parts[0].text])
                return response.text
                
        try:
            full_text = await asyncio.to_thread(run_vision)
            
            if full_text and stream:
                from assistant.core.event_bus import bus, EventType
                from assistant.core.llm_utils import split_sentences
                import uuid
                
                sentences = split_sentences(full_text)
                message_id = str(uuid.uuid4())
                for sentence in sentences:
                    bus.emit(EventType.LLM_STREAMING, (sentence, None, message_id))
                    
            return full_text
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return "Failed to analyze screen."
