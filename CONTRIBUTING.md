# Contributing to Jarvis 2.0

First off, thank you for considering contributing to Jarvis 2.0! It's people like you that make Jarvis such a powerful tool.

## Developer Environment Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Arnab27622/Jarvis-2.0.git](https://github.com/Arnab27622/Jarvis-2.0.git)
   cd Jarvis-2.0
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in your API keys (Gemini, OpenRouter, etc.).

5. **Frontend Setup:**
   ```bash
   cd jarvis-ui
   npm install
   ```

## Adding New Commands

Jarvis uses a flexible modular command registry. To add a new voice command:

1. Create a new Python file in `assistant/automation/features/` or `assistant/automation/integrations/`.
2. Import the command registry decorators:
   ```python
   from assistant.core.registry import on_keyword, on_regex, on_fuzzy
   from assistant.core.speak_selector import speak
   ```
3. Define your function and decorate it. For example, a keyword match:
   ```python
   @on_keyword(["check status", "system status"])
   def report_status(text: str):
       speak("All systems are fully operational.")
   ```
4. The registry will automatically discover and register your command when Jarvis starts!

## Adding New Specialized Agents

Jarvis 2.0 uses a Multi-Agent architecture routed by `LLMManager`. To add a new persona:
1. Create a new file in `assistant/agents/` (e.g., `analyst.py`).
2. Inherit from `BaseAgent` and define a robust `system_prompt`.
3. Provide any custom tools (e.g., `tools=[analyze_data]`).
4. Register your new agent in the `__init__` method of `assistant/core/llm_manager.py`.

## Adding New LLM Providers

To add a new LLM provider (like Anthropic or OpenAI):
1. Open `assistant/core/llm_manager.py` (or `base.py` for agent-specific clients).
2. Add your provider's logic and configure the API endpoint.
3. Always yield tokens via streaming if the provider supports it, to ensure the UI and Kokoro TTS pipeline remain completely real-time.

## Code Style Guide

- **Formatting**: We use `ruff` for linting and formatting. Run `ruff check .` before committing.
- **Type Hints**: Please use Python type hints for all function signatures. We use `mypy` to enforce this.
- **Logging**: Do not use `print()`. Use the centralized logger:
  ```python
  from assistant.core.logger import get_logger
  logger = get_logger("MyModule")
  logger.info("Initializing...")
  ```
- **Docstrings**: Include descriptive docstrings for classes and complex functions.
