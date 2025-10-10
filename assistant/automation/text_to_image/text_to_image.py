import base64
import requests
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

# Load environment variables from .env file for API key security
load_dotenv()


def generate_image_from_text(prompt_text):
    """
    Generate high-quality images from text prompts using Stability AI's Stable Diffusion XL API.

    This function interfaces with Stability AI's advanced image generation model to create
    1024x1024 pixel images based on textual descriptions. The generated images are saved
    to a local directory for user access.

    Args:
        prompt_text (str): The descriptive text prompt that defines what image to generate.
                         Example: "A serene landscape with mountains and a lake at sunset"

    Process:
        1. Configures API request with optimal parameters for quality image generation
        2. Sends prompt to Stability AI's Stable Diffusion XL model
        3. Handles API response and error checking
        4. Decodes base64 image data and saves as PNG file
        5. Provides voice confirmation to user

    API Configuration:
        - Model: Stable Diffusion XL 1024 v1.0 (high-resolution capable)
        - Steps: 40 (balance between quality and generation time)
        - Resolution: 1024x1024 pixels (high definition)
        - CFG Scale: 5 (creativity vs prompt adherence balance)
        - Negative Prompt: "blurry, bad" (automatic quality improvement)

    Image Quality Features:
        - High resolution 1024x1024 output
        - 40-step generation for detailed results
        - Automatic negative prompt for quality enhancement
        - Seed-based reproducibility

    Raises:
        Exception: If the API returns a non-200 HTTP status code, raises an exception
                  with the detailed error response from the API.

    Example:
        >>> generate_image_from_text("A cyberpunk cityscape at night with neon lights")
        # Generates and saves a cyberpunk-themed image
        # Speaks: "Image saved in Images folder"

    Note:
        Requires a valid Stability AI API key set in the STABILITY_API_KEY environment variable.
        Generated images are saved in the project's data/images directory with seed-based naming.
    """
    # Stability AI API endpoint for Stable Diffusion XL
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    # API request body with generation parameters optimized for quality
    body = {
        "steps": 40,  # Number of denoising steps (higher = better quality but slower)
        "width": 1024,  # Output image width in pixels
        "height": 1024,  # Output image height in pixels
        "seed": 0,  # Random seed (0 = random each time)
        "cfg_scale": 5,  # How closely to follow the prompt (1-20, 5-10 recommended)
        "samples": 1,  # Number of images to generate
        "text_prompts": [
            {"text": prompt_text, "weight": 1},  # Main positive prompt
            {
                "text": "blurry, bad",
                "weight": -1,
            },  # Negative prompt to avoid poor quality
        ],
    }

    # API request headers with authentication
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}",
    }

    # Send POST request to Stability AI API
    response = requests.post(
        url,
        headers=headers,
        json=body,
    )

    # Check for API errors and raise exception if request failed
    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    # Parse JSON response containing generated image data
    data = response.json()

    # Define storage directory for generated images
    folder_path = r"C:\Users\ARNAB DEY\MyPC\Python\Projects\Jarvis 2.0\data\images"
    os.makedirs(folder_path, exist_ok=True)  # Create directory if it doesn't exist

    # Process and save each generated image from the response
    for i, image in enumerate(data["artifacts"]):
        # Create filename using the generation seed for unique identification
        filename = f'{folder_path}/txt2img_{image["seed"]}.png'
        with open(filename, "wb") as f:
            # Decode base64 image data and save as PNG file
            f.write(base64.b64decode(image["base64"]))
        speak(f"Image saved in Images folder.")


if __name__ == "__main__":
    """
    Standalone execution entry point for text-to-image generation.

    When run directly, this script prompts the user for a text description
    and generates an image based on the provided prompt.

    Usage:
        python text_to_image.py
        # Then enter your image description when prompted
    """
    user_prompt = input("Enter the text prompt for the image generation: ")
    generate_image_from_text(user_prompt)
