from assistant.agents.base import BaseAgent
from assistant.core.tools import search_web
from assistant.core.logger import get_logger

logger = get_logger("CoderAgent")

# The Coder gets search_web so it can look up documentation if needed.
# In the future, we can add file read/write and terminal execution tools here.
CODER_TOOLS = [search_web]

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Coder",
            system_prompt=(
                "You are the Coder Agent for JARVIS. You specialize in writing, explaining, and debugging code.\n"
                "CRITICAL SYSTEM RULES:\n"
                "1. ALWAYS wrap ALL code inside standard markdown code blocks (```language ... ```). The Text-to-Speech engine relies on these blocks to avoid reading the raw code aloud.\n"
                "2. Provide a brief, spoken-friendly summary of what the code does BEFORE the code block. DO NOT read the code line-by-line."
            ),
            tools=CODER_TOOLS
        )
