"""
Vision Module - Context-Aware Screen Analysis

This module allows Jarvis to "see" the screen by capturing screenshots
and passing them to a multimodal LLM (Gemini).
"""

import pyautogui
from PIL import Image
import io
import base64
from typing import Optional
from assistant.core.logger import get_logger

logger = get_logger("Vision")

def capture_screen() -> Optional[Image.Image]:
    """
    Captures the primary screen and returns a PIL Image.
    Scales down the image to reduce payload size and token usage.
    """
    try:
        # Capture the whole screen
        img = pyautogui.screenshot()
        
        # Scale down for faster API transmission while maintaining readability
        # 1920x1080 -> 1280x720 is usually sufficient for Gemini Vision
        img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        
        logger.info(f"Captured screen screenshot: {img.size}")
        return img
    except Exception as e:
        logger.error(f"Failed to capture screen: {e}")
        return None

def encode_image_base64(img: Image.Image) -> Optional[str]:
    """
    Encodes a PIL Image into a base64 string.
    """
    if not img:
        return None
    try:
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    except Exception as e:
        logger.error(f"Failed to encode image: {e}")
        return None
