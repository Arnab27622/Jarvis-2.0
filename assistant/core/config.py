"""
Centralized Configuration System for Jarvis 2.0

Provides a single, validated, type-safe source of truth for all configuration.
Replaces scattered os.getenv() and load_dotenv() calls across the codebase.

Usage:
    from assistant.core.config import config

    # API keys (loaded from .env)
    config.gemini_api_key       # Optional[str]
    config.openrouter_api_key   # Optional[str]

    # Paths (auto-derived from project root)
    config.project_root         # Path
    config.data_dir             # Path
    config.models_dir           # Path

    # TTS settings
    config.tts_voice            # str (default: "am_michael")
    config.tts_speed            # float (default: 1.08)

    # Check if a provider is available
    config.has_gemini           # bool
"""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (directory containing main.py)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "main.py").exists():
            return current
        current = current.parent
    # Fallback: assume 3 levels up from assistant/core/config.py
    return Path(__file__).resolve().parent.parent.parent


# Load .env once at import time
PROJECT_ROOT = _find_project_root()
load_dotenv(PROJECT_ROOT / ".env")


class JarvisConfig:
    """
    Centralized configuration for Jarvis 2.0.

    All API keys are loaded from environment variables (via .env file).
    Paths are derived from the project root directory.
    Runtime settings have sensible defaults and can be updated at runtime.
    """

    def __init__(self) -> None:
        # ── Project paths ──
        self.project_root: Path = PROJECT_ROOT
        self.data_dir: Path = self.project_root / "data"
        self.models_dir: Path = self.project_root / "models"
        self.brain_data_dir: Path = self.data_dir / "brain_data"
        self.images_dir: Path = self.data_dir / "images"
        self.screenshots_dir: Path = self.data_dir / "screenshots"
        self.alarm_data_dir: Path = self.data_dir / "alarm_data"
        self.reminder_data_dir: Path = self.data_dir / "reminder_data"
        self.sounds_dir: Path = self.data_dir / "sounds"
        self.logs_dir: Path = self.data_dir / "logs"

        # ── API Keys (all Optional — Jarvis works with whatever is available) ──
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
        self.hf_token: Optional[str] = os.getenv("HF_TOKEN")
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.stability_api_key: Optional[str] = os.getenv("STABILITY_API_KEY")
        self.cloudflare_api_token: Optional[str] = os.getenv("CLOUDFLARE_API_TOKEN")
        self.cloudflare_account_id: Optional[str] = (
            os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CLOUDFLARE_ACOUNT_ID")
        )
        self.pollination_api_key: Optional[str] = os.getenv("POLLINATION_API_KEY")
        self.news_api_key: Optional[str] = os.getenv("NEWS_API_KEY")
        self.weather_api_key: Optional[str] = os.getenv("WEATHER_API_KEY")
        self.youtube_api_key: Optional[str] = os.getenv("YOUTUBE_API_KEY")
        self.serpapi_api_key: Optional[str] = os.getenv("SERPAPI_API_KEY")

        # ── TTS Settings ──
        self.kokoro_model_path: Path = self.models_dir / "kokoro-v1.0.onnx"
        self.kokoro_voices_path: Path = self.models_dir / "voices-v1.0.bin"
        self.tts_voice: str = "am_michael"
        self.tts_speed: float = 1.08
        self.tts_language: str = "en-us"
        self.ack_sound_path: Path = self.sounds_dir / "ack_chirp.wav"
        
        # UI Settings
        self.theme: str = "cyan"

        # Load overrides from config.json
        self._load_json_config()

        # ── Speech Recognition Settings ──
        self.stt_energy_threshold: int = 35100
        self.stt_pause_threshold: float = 1.2
        self.stt_non_speaking_duration: float = 0.8
        self.stt_phrase_threshold: float = 0.3
        self.stt_calibration_duration: int = 2
        self.stt_listen_timeout: int = 5
        self.stt_phrase_time_limit: int = 30

        # ── LLM Settings ──
        self.llm_max_history: int = 10
        self.llm_max_tokens: int = 800
        self.llm_temperature: float = 0.7
        self.llm_timeout: int = 60

        # ── Music Player ──
        self.music_dir: str = os.path.join(os.path.expanduser("~"), "Music")

        # ── Data Files ──
        self.chat_history_path: Path = self.brain_data_dir / "chat_history.json"
        self.qna_data_path: Path = self.brain_data_dir / "qna_data.json"
        self.remembered_info_path: Path = self.data_dir / "remembered_info.json"

        # ── Web Server ──
        self.web_port: int = 1410

        # ── Activity Monitor ──
        self.activity_initial_delay: int = 100
        self.activity_check_interval: int = 120
        self.activity_inactivity_threshold: int = 180

        # Ensure critical directories exist
        self._ensure_directories()

        # Print provider status at startup
        self._log_provider_status()

    def _ensure_directories(self) -> None:
        """Create essential directories if they don't exist."""
        dirs = [
            self.data_dir, self.brain_data_dir, self.images_dir,
            self.screenshots_dir, self.alarm_data_dir,
            self.reminder_data_dir, self.sounds_dir, self.logs_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _load_json_config(self) -> None:
        """Load settings overrides from config.json."""
        self.config_file = self.project_root / "config.json"
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.tts_voice = data.get("tts_voice", self.tts_voice)
                    self.tts_speed = data.get("tts_speed", self.tts_speed)
                    self.theme = data.get("theme", self.theme)
            except Exception as e:
                print(f"[Config] Error loading config.json: {e}")

    def save_settings(self, data: dict) -> None:
        """Update and save settings to config.json."""
        if "tts_voice" in data:
            self.tts_voice = data["tts_voice"]
        if "tts_speed" in data:
            self.tts_speed = float(data["tts_speed"])
        if "theme" in data:
            self.theme = data["theme"]
        
        try:
            with open(self.config_file, "w") as f:
                json.dump({
                    "tts_voice": self.tts_voice,
                    "tts_speed": self.tts_speed,
                    "theme": self.theme
                }, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config.json: {e}")

    def _log_provider_status(self) -> None:
        """Report which API providers are configured at startup."""
        providers = {
            "Gemini": self.has_gemini,
            "OpenRouter": self.has_openrouter,
            "HuggingFace": self.has_huggingface,
            "Groq": self.has_groq,
            "Stability AI": self.has_stability,
            "Cloudflare": self.has_cloudflare,
            "Pollinations": self.has_pollinations,
            "YouTube": self.has_youtube,
            "News API": self.has_news,
            "Weather API": self.has_weather,
            "SerpAPI": self.has_serpapi,
        }
        available = [name for name, status in providers.items() if status]
        missing = [name for name, status in providers.items() if not status]

        print(f"[Config] {len(available)} providers configured: {', '.join(available)}")
        if missing:
            print(f"[Config] {len(missing)} providers unavailable (no API key): {', '.join(missing)}")

    # ── Convenience properties for provider availability ──
    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def has_huggingface(self) -> bool:
        return bool(self.hf_token)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_stability(self) -> bool:
        return bool(self.stability_api_key)

    @property
    def has_cloudflare(self) -> bool:
        return bool(self.cloudflare_api_token and self.cloudflare_account_id)

    @property
    def has_pollinations(self) -> bool:
        return bool(self.pollination_api_key)

    @property
    def has_youtube(self) -> bool:
        return bool(self.youtube_api_key)

    @property
    def has_news(self) -> bool:
        return bool(self.news_api_key)

    @property
    def has_weather(self) -> bool:
        return bool(self.weather_api_key)

    @property
    def has_serpapi(self) -> bool:
        return bool(self.serpapi_api_key)

    def get_available_llm_providers(self) -> list[str]:
        """Returns a list of available LLM provider names."""
        providers = []
        if self.has_gemini:
            providers.append("Gemini")
        if self.has_huggingface:
            providers.append("HuggingFace")
        if self.has_openrouter:
            providers.append("OpenRouter")
        if self.has_groq:
            providers.append("Groq")
        # g4f is always available (no API key needed)
        providers.append("GPT4Free")
        return providers


# Singleton instance — import this everywhere
config = JarvisConfig()
