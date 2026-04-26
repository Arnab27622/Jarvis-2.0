# Directory Structure

## Root Level
- `main.py`: Project entry point.
- `requirements.txt`: Python dependencies.
- `setup.py` / `pyproject.toml`: Packaging configuration.
- `.env.example`: Template for environment variables.
- `test.py`: Root-level testing/experimentation script.

## Assistant Package (`assistant/`)
- `core/`: Central logic and engine.
- `LLM/`: LLM integration wrappers.
- `automation/`: OS and GUI automation scripts.
- `activities/`: Specific task implementations.
- `interface/`: UI components and interaction handlers.
- `secondary_tts/`: Alternative Text-to-Speech engines.

## Data Directory (`data/`)
- `claps/`: Audio files for clap detection.
- `dlg_data/`: Dialog or conversation data.
- `images/`: Visual assets and screenshots.
- `noise2/`: Audio processing/noise profiles.
- `reminder_data/`: JSON and WAV files for reminders.
- `Clap_Detect_Model.pth`: Pre-trained model for clap detection.

---
*Last updated: 2026-04-26 after initial mapping*
