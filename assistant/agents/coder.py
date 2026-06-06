from assistant.agents.base import BaseAgent
from assistant.core.tools import search_web, execute_terminal_command, execute_code
from assistant.core.logger import get_logger

logger = get_logger("CoderAgent")

CODER_TOOLS = [search_web, execute_terminal_command, execute_code]

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Coder",
            system_prompt=(
                "You are the Coder Agent for JARVIS. You specialize in writing, explaining, and debugging code.\n"
                "CRITICAL SYSTEM RULES:\n"
                "1. ALWAYS wrap ALL code inside standard markdown code blocks (```language ... ```). The Text-to-Speech engine relies on these blocks to avoid reading the raw code aloud.\n"
                "2. Provide a brief, spoken-friendly summary of what the code does BEFORE the code block. DO NOT read the code line-by-line.\n"
                "3. You have access to execute_terminal_command and execute_code. If you need to run a multi-line script in python, javascript, node, batch, powershell, c, or c++, use the execute_code tool. If you need to run standard CLI commands or single-line scripts, use execute_terminal_command. The user will be prompted to approve the execution before it runs."
            ),
            tools=CODER_TOOLS
        )
