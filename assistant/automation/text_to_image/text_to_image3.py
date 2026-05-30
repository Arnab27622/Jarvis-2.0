"""Module for generating images from text prompts using the Pollinations AI API."""

import requests
import os
import random
from urllib.parse import quote
from assistant.core.config import config
from assistant.core.speak_selector import speak
from typing import Optional

def generate_image_from_text(prompt_text: str) -> Optional[str]:
    """
    Generates an image from a text prompt using the Pollinations AI Flux model.

    Args:
        prompt_text: The description of the image to be generated.

    Returns:
        The file path of the saved image if successful, otherwise None.
    """
    api_key = config.pollination_api_key
    if not api_key:
        speak("I encountered an error while trying to generate that image.")
        return None

    # Image Settings
    model = "flux"
    width = 1024
    height = 1024
    seed = random.randint(1, 999999)
    enhance = "true"
    steps = 30
    guidance = 7
    safe = "true"
    image_format = "jpg"
    
    negative_prompt = (
        "blurry, distorted, low quality, pixelated, bad anatomy, deformed face, extra fingers, mutated hands, poorly drawn eyes, text, watermark, logo, cropped, duplicate objects, oversaturated, ugly, distorted proportions, artifacting, low detail, out of frame"
    )

    base_url = "https://gen.pollinations.ai/image/"

    # URL encode prompts to safely include them in the GET request URL
    encoded_prompt = quote(prompt_text)
    encoded_negative_prompt = quote(negative_prompt)

    url = (
        f"{base_url}{encoded_prompt}"
        f"?model={model}"
        f"&width={width}"
        f"&height={height}"
        f"&seed={seed}"
        f"&enhance={enhance}"
        f"&steps={steps}"
        f"&guidance={guidance}"
        f"&negative_prompt={encoded_negative_prompt}"
        f"&safe={safe}"
        f"&format={image_format}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        print(f"Generating image for prompt: {prompt_text[:50]}...")
        
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"API Error (Status {response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"Image generation failed: {e}")
        speak("I encountered an error while trying to generate that image.")
        return None

    folder_path = str(config.images_dir)
    os.makedirs(folder_path, exist_ok=True)

    filename = os.path.join(folder_path, f"txt2img_{seed}.{image_format}")
    
    with open(filename, "wb") as f:
        f.write(response.content)

    return filename


if __name__ == "__main__":
    """Executes a test run of the image generation process."""
    user_prompt = input("Enter the text prompt for the image generation: ")
    if user_prompt.strip():
        generate_image_from_text(user_prompt)
    else:
        print("No prompt provided.")
