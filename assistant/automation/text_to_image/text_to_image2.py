"""
Cloudflare AI Flux-1-Schnell Image Generation Module

This module provides fast image generation using Cloudflare's AI Workers running the 
Black Forest Labs flux-1-schnell model.

Requires environment variables:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID (or CLOUDFLARE_ACOUNT_ID)
"""

import time
import requests
import base64
from typing import Tuple, Optional
import os
from assistant.core.config import config
from assistant.core.speak_selector import speak

# Default storage path for generated images
file_path = str(config.images_dir)


def validate_token() -> bool:
    """
    Validate the Cloudflare AI API token and Account ID before making image generation requests.

    Returns:
        bool: True if tokens pass basic validation checks, False otherwise
    """
    token = config.cloudflare_api_token
    account_id = config.cloudflare_account_id
    
    if not token or not account_id:
        print("❌ CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID environment variable not set")
        speak("Cloudflare API token or Account ID is not set. Please check your environment variables.")
        return False

    return True


def generate(
    prompt: str,
    seed: int = 42,
    width: int = 1024,
    height: int = 1024,
    steps: int = 7,
    image_path: str = None,
) -> Tuple[bool, Optional[str]]:
    """
    Generate images using Cloudflare's AI Workers (flux-1-schnell).

    Args:
        prompt (str): Text description of the desired image content
        seed (int): Random seed for reproducible results (default: 42)
        width (int): Output image width in pixels (default: 1024)
        height (int): Output image height in pixels (default: 1024)
        steps (int): Number of generation steps (default: 7)
        image_path (str, optional): Custom file path for saving the image

    Returns:
        Tuple[bool, Optional[str]]:
            - Success status (True/False)
            - File path if successful, error message if failed
    """
    # Validate token first to avoid failed API calls
    if not validate_token():
        return False, "Token validation failed"

    # Generate timestamp-based filename if no custom path provided
    if image_path is None:
        image_path = os.path.join(file_path, f"image_{int(time.time()*1000)}.jpg")

    # Ensure storage directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    token = config.cloudflare_api_token
    account_id = config.cloudflare_account_id

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # API request payload with generation parameters
    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, distorted, low quality, pixelated, bad anatomy, deformed face, extra fingers, mutated hands, poorly drawn eyes, text, watermark, logo, cropped, duplicate objects, oversaturated, ugly, distorted proportions, artifacting, low detail, out of frame",
        "width": width,
        "height": height,
        "num_steps": steps,
        "guidance": 5,
        "seed": seed
    }

    try:
        print(f"Generating image with prompt: {prompt[:100]}...")

        # Make API request with 60-second timeout
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()
        
        if not data.get("success"):
            error_msg = f"Cloudflare API Error: {data.get('errors')}"
            print(error_msg)
            return False, error_msg

        # Extract base64 image data from response
        base64_image_data = data["result"]["image"]
        if not base64_image_data:
            error_msg = "No image data received in response"
            print(error_msg)
            return False, error_msg

        # Decode base64 data and save as image file
        image_bytes = base64.b64decode(base64_image_data)

        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)

        # Remove speak, image_manager will handle it
        return True, image_path

    except requests.exceptions.Timeout:
        error_msg = "API request timed out"
        print(error_msg)
        speak("The image generation is taking too long. Please try again.")
        return False, error_msg

    except requests.exceptions.HTTPError as e:
        error_msg = f"API returned error: {e.response.status_code} - {e.response.text}"
        print(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        return False, error_msg


if __name__ == "__main__":
    use_input = input("Use custom prompt? (y/n): ").lower().strip()
    if use_input == "y":
        prompt = input("Enter the prompt: ")
    else:
        prompt = "A futuristic female AI hologram assistant"
    if prompt.strip():
        success, result_path = generate(prompt)
        if success:
            print(f"Image successfully saved at: {result_path}")
        else:
            print(f"Failed to generate image: {result_path}")
    else:
        print("No prompt provided")