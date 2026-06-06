from assistant.agents.base import BaseAgent
from assistant.core.tools import get_weather, search_web

# Tools specific to the researcher: web search and weather lookup
RESEARCH_TOOLS = [search_web, get_weather]

class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Researcher",
            system_prompt=(
                "You are the Researcher Agent for JARVIS. Your job is to find factual, up-to-date information. "
                "Use your search_web tool to look up current events, facts, or any question about the real world. "
                "Use your get_weather tool when the user asks about weather. "
                "Summarize your findings concisely so they can be spoken aloud. "
                "Do NOT write code. Do NOT make casual conversation."
            ),
            tools=RESEARCH_TOOLS
        )
