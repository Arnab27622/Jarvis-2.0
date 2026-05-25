# Jarvis 2.0 - Advanced Personal AI Voice Assistant

Jarvis 2.0 is an advanced, voice-controlled AI assistant written in Python 3.11. It leverages local and cloud-based models to provide an interactive, conversational experience, along with powerful system automations.

## Features

* **Advanced Text-to-Speech (TTS):** Uses Kokoro-ONNX for fast, high-quality, and natural-sounding offline voice synthesis.
* **Large Language Model (LLM) Integration:** Intelligent routing defaults to Gemini 3.1 Flash Lite for lightning-fast conversational responses, with automatic sequential fallbacks to HuggingFace, OpenRouter, and GPT4Free.
* **Intelligent Automations:**
  * **System Control:** Open and close applications and websites.
  * **Web Information:** Integrated Wikipedia search, direct Google Custom Search, real-time news, and weather updates.
  * **Text-to-Image:** Generates high-quality images via a unified image manager routing between Pollinations AI (Flux), Cloudflare AI (Flux-1-Schnell), and Stability AI (Stable Diffusion XL).
  * **YouTube Automation:** Play specific videos, control playback, and adjust volume using voice.
  * **Utilities:** Set alarms, tell jokes, report current location, check internet speed, and LLM-powered semantic memory for taking persistent notes and recalling them contextually.

## Prerequisites

* **Python 3.11** (Required. Python 3.12+ may have compatibility issues with certain audio libraries).
* A working microphone and speakers.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Arnab27622/Jarvis-2.0.git
   cd Jarvis-2.0
   ```

2. **Create and activate a virtual environment (Python 3.11):**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   *Note: If `pyaudio` fails to install, you may need to install the appropriate wheel for your Python version, or install it via conda.*

4. **Setup Environment Variables:**
   Create a `.env` file in the root directory and add the following keys based on the features you want to use:
   ```env
   # Core LLMs
   GEMINI_API_KEY=your_gemini_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   HF_TOKEN=your_huggingface_token
   GROQ_API_KEY=your_groq_api_key

   # Image Generation Models
   STABILITY_API_KEY=your_stability_api_key
   CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
   CLOUDFLARE_ACOUNT_ID=your_cloudflare_account_id
   POLLINATION_API_KEY=your_pollinations_api_key

   # Automations
   NEWS_API_KEY=your_news_api_key
   WEATHER_API_KEY=your_openweathermap_api_key
   YOUTUBE_API_KEY=your_youtube_api_key
   SERPAPI_API_KEY=your_serpapi_key
   ```

5. **Download Kokoro ONNX Models:**
   The assistant requires the Kokoro TTS models. They are automatically managed, but ensure you have the `kokoro-v0_19.onnx` and `voices.json` correctly placed if doing a manual setup.

## Usage

Start the assistant by running:
```bash
python main.py
```
Wait for the "Initializing Voice Module" message to finish and then speak your command.

## Codebase Structure
The project is completely type-hinted and documented:
- `main.py`: Entry point for the assistant.
- `assistant/core/`: Core modules for Wake word detection, TTS (`mouth.py`), Speech Recognition (`ear.py`), and LLM routing (`llm_manager.py`).
- `assistant/interface/`: Command routing and GUI handling.
- `assistant/automation/`: All features, integrations (like `image_manager.py` and `task_schedule_automation.py`), and intelligent background capabilities.
