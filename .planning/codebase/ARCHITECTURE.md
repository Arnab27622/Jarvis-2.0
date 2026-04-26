# Architecture Overview

## System Pattern
The project follows a modular monolithic architecture, organized into functional packages under the `assistant/` directory.

## Core Components
- **Entry Point (`main.py`)**: Orchestrates the startup and main loop of the assistant.
- **Core Logic (`assistant/core`)**: Likely handles the central processing and state management.
- **LLM Layer (`assistant/LLM`)**: Manages communication with external AI providers.
- **Automation Layer (`assistant/automation`)**: Interfaces with the OS for task execution (GUI automation, system controls).
- **Interface Layer (`assistant/interface`)**: Handles user interaction (voice/UI).

## Data Flow
1. **Input**: Voice (SpeechRecognition) or other triggers.
2. **Processing**: Core logic analyzes input, potentially calling LLM services.
3. **Action**: Executes tasks via automation or provides feedback via TTS/UI.
4. **Output**: Voice output (edge-tts/pyttsx3) or visual feedback.

---
*Last updated: 2026-04-26 after initial mapping*
