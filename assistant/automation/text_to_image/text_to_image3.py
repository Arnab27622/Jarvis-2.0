import requests
import os
import random
from urllib.parse import quote
from dotenv import load_dotenv
from assistant.core.speak_selector import speak
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file for API key security
load_dotenv()

def generate_image_from_text(prompt_text: str) -> Optional[bool]:
    """
    Generate high-quality images from text prompts using Pollinations AI.

    This function interfaces with the Pollinations AI image generation model (Flux) to create
    1024x1024 pixel images based on textual descriptions. The generated images are saved
    to a local directory for user access.

    Args:
        prompt_text (str): The descriptive text prompt that defines what image to generate.
                         Example: "A serene landscape with mountains and a lake at sunset"

    Process:
        1. Configures API request with optimal parameters for quality image generation
        2. Sends GET request with encoded parameters to Pollinations AI
        3. Handles API response and error checking
        4. Saves the returned image bytes as a JPG file
        5. Provides voice confirmation to user

    API Configuration:
        - Model: flux (Best overall quality)
        - Width/Height: 1024x1024
        - Steps: 30 (Higher = better quality but slower)
        - Guidance: 7 (Higher = follows prompt more strictly)
        - Enhance: True (Automatic prompt enhancement)
        - Safe: True (Safe mode enabled)
        - Negative Prompt: Standard bad quality keywords (blurry, deformed, etc.)

    Image Quality Features:
        - High resolution 1024x1024 output
        - Automatic negative prompt for quality enhancement
        - Random seed-based reproducibility

    Returns:
        Optional[bool]: False if generation failed, None otherwise.

    Example:
        >>> generate_image_from_text("A cyberpunk cityscape at night with neon lights")
        # Generates and saves a cyberpunk-themed image
        # Speaks: "Image saved in Images folder"
    """
    # Retrieve the API key from environment variable
    api_key = os.getenv("POLLINATION_API_KEY")
    if not api_key:
        speak("I encountered an error while trying to generate that image.")
        return False

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
    
    # Negative prompt for quality control
    negative_prompt = (
        "blurry, low quality, bad anatomy, extra fingers, "
        "deformed face, text, watermark, logo, cropped, duplicate, low resolution"
    )

    # Base URL for Pollinations AI image generation
    base_url = "https://gen.pollinations.ai/image/"

    # URL encode prompts to safely include them in the GET request URL
    encoded_prompt = quote(prompt_text)
    encoded_negative_prompt = quote(negative_prompt)

    # Build the full request URL
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
        
        # Send GET request to Pollinations AI
        response = requests.get(url, headers=headers, timeout=60)
        
        # Check for API errors
        if response.status_code != 200:
            raise Exception(f"API Error (Status {response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"Image generation failed: {e}")
        speak("I encountered an error while trying to generate that image.")
        return False

    # Define storage directory for generated images
    folder_path = r"C:\Users\ARNAB DEY\MyPC\Python\Projects\Jarvis 2.0\data\images"
    os.makedirs(folder_path, exist_ok=True)  # Create directory if it doesn't exist

    # Create filename using the generation seed for unique identification
    filename = os.path.join(folder_path, f"txt2img_{seed}.{image_format}")
    
    # Save the returned image bytes to file
    with open(filename, "wb") as f:
        f.write(response.content)

    speak("Image saved in Images folder.")


if __name__ == "__main__":
    """
    Standalone execution entry point for text-to-image generation.

    When run directly, this script prompts the user for a text description
    and generates an image based on the provided prompt.
    """
    user_prompt = input("Enter the text prompt for the image generation: ")
    if user_prompt.strip():
        generate_image_from_text(user_prompt)
    else:
        print("No prompt provided.")
