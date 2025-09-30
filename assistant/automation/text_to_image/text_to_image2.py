"""
Decohere AI Turbo Image Generation Module

Warning: The Decohere AI API token expires every 5 minutes for security reasons.
To obtain a new token:
1. Visit https://www.decohere.ai/realtime
2. Create an image on their platform
3. Open browser Developer Tools (F12) and go to Network tab
4. Look for 'turbo' network requests and copy the Authorization token
5. Update your DECOHERE_AI environment variable with the new token

This module provides fast image generation using Decohere AI's Turbo model with
optimized parameters for quick turnaround times while maintaining quality.
"""

import time
import requests
import base64
from typing import Tuple, Optional
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

# Load environment variables for API key access
load_dotenv()

# Default storage path for generated images
file_path = r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\images"


def validate_token() -> bool:
    """
    Validate the Decohere AI API token before making image generation requests.

    Performs basic validation checks on the token to ensure it's properly set
    and appears to be in the correct format before attempting API calls.

    Returns:
        bool: True if token passes basic validation checks, False otherwise

    Validation Checks:
        - Token exists in environment variables
        - Token has reasonable length (minimum 20 characters)
        - Basic format validation

    Example:
        >>> validate_token()
        Token length: 145 characters
        True
    """
    token = os.getenv("DECOHERE_AI")
    if not token:
        print("❌ DECOHERE_AI environment variable not set")
        speak("DECOHERE AI token is not set. Please check your environment variables.")
        return False

    # Check token length and format
    token_length = len(token)
    print(f"🔑 Token length: {token_length} characters")

    if token_length < 20:
        print("⚠️  Token seems unusually short")
        return False

    return True


def generate(
    prompt: str,
    seed: int = 1800647681,
    width: int = 1024,
    height: int = 576,
    steps: int = 5,
    enhance: bool = True,
    safety_filter: bool = True,
    image_path: str = None,
) -> Tuple[bool, Optional[str]]:
    """
    Generate images using Decohere AI's Turbo API with optimized fast generation.

    This function provides rapid image generation with quality optimization through
    intelligent parameter defaults. It's designed for quick turnaround while
    maintaining good image quality for most use cases.

    Args:
        prompt (str): Text description of the desired image content
        seed (int): Random seed for reproducible results (default: 1800647681)
        width (int): Output image width in pixels
        height (int): Output image height in pixels
        steps (int): Number of generation steps (more steps = higher quality but slower)
        enhance (bool): Enable quality enhancement algorithms
        safety_filter (bool): Enable content safety filtering
        image_path (str, optional): Custom file path for saving the image

    Returns:
        Tuple[bool, Optional[str]]:
            - Success status (True/False)
            - File path if successful, error message if failed

    Recommended Image Dimensions:
        - Square: 768x768 pixels
        - Portrait: 1024x576 pixels (default)
        - Landscape: 576x1024 pixels

    Performance Notes:
        - Default 5 steps provide fast generation with acceptable quality
        - Increase steps to 10-15 for higher quality when speed isn't critical
        - Turbo model optimized for rapid generation (seconds vs minutes)

    Example:
        >>> generate("A beautiful sunset over mountains")
        (True, "C:/Users/.../image_1640995200000.jpg")
    """
    # Validate token first to avoid failed API calls
    if not validate_token():
        return False, "Token validation failed"

    # Generate timestamp-based filename if no custom path provided
    if image_path is None:
        image_path = f"{file_path}/image_{int(time.time()*1000)}.jpg"

    # Ensure storage directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    token = os.getenv("DECOHERE_AI")

    # Decohere AI Turbo API endpoint
    url = "https://turbo.decohere.ai/generate/turbo"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    # API request payload with generation parameters
    payload = {
        "prompt": prompt,
        "seed": seed,
        "width": width,
        "height": height,
        "steps": steps,
        "enhance": enhance,
        "safety_filter": safety_filter,
    }

    try:
        print(f"Generating image with prompt: {prompt[:100]}...")

        # Make API request with 60-second timeout
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Extract base64 image data from response
        base64_image_data = response.json().get("image", "")
        if not base64_image_data:
            error_msg = "No image data received in response"
            print(error_msg)
            return False, error_msg

        # Decode base64 data and save as image file
        image_bytes = base64.b64decode(base64_image_data)

        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)

        speak(f"Image has been successfully generated and saved in the images folder.")

        return True, image_path

    except requests.exceptions.Timeout:
        error_msg = "API request timed out"
        print(error_msg)
        speak("The image generation is taking too long. Please try again.")
        return False, error_msg

    except requests.exceptions.HTTPError as e:
        error_msg = f"API returned error: {e.response.status_code} - {e.response.text}"
        print(error_msg)

        # Handle specific HTTP status codes with appropriate user feedback
        if e.response.status_code == 401:
            print("Authentication failed. Please check your DECOHERE AI token.")
        elif e.response.status_code == 429:
            print("Too many requests. Please wait before generating another image.")
        else:
            print("Sorry, there was an error generating the image.")

        return False, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {e}"
        print(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        return False, error_msg


def test_token():
    """
    Test Decohere AI token validity and API connectivity.

    Performs comprehensive testing of the API token and connection to ensure
    the image generation service is accessible and properly configured.

    Tests Performed:
        - Token existence and basic validation
        - Token masking for security display
        - API endpoint connectivity with minimal test request
        - Response status validation

    Output:
        Diagnostic information about token and API status

    Example:
        >>> test_token()
        Testing DECOHERE_AI token...
        Token appears valid: sk-1234567890...1234567890
        API connectivity test passed!
    """
    print("Testing DECOHERE_AI token...")

    if validate_token():
        token = os.getenv("DECOHERE_AI")
        # Mask token for secure display (show first and last 10 characters)
        masked_token = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else token
        print(f"Token appears valid: {masked_token}")

        # Test API connectivity with minimal request to avoid charges
        url = "https://turbo.decohere.ai/generate/turbo"
        headers = {"Authorization": f"Bearer {token}"}
        test_payload = {"prompt": "test", "width": 16, "height": 16, "steps": 1}

        try:
            response = requests.post(
                url, headers=headers, json=test_payload, timeout=10
            )
            if response.status_code == 200:
                print("API connectivity test passed!")
            else:
                print(f"API returned status: {response.status_code}")
        except Exception as e:
            print(f"API test failed: {e}")
    else:
        print("Token validation failed")


if __name__ == "__main__":
    """
    Standalone testing and demonstration entry point.

    When run directly, this script provides:
    1. Token validation testing
    2. Interactive prompt input
    3. Image generation demonstration
    4. Result reporting

    Usage:
        python text_to_image2.py
        # Follow the prompts to test token and generate images
    """
    # Test token first to ensure API accessibility
    test_token()
    print("\n" + "=" * 50)

    # Interactive prompt selection
    use_input = input("Use custom prompt? (y/n): ").lower().strip()

    if use_input == "y":
        prompt = input("Enter the prompt: ")
    else:
        # Use a simple test prompt for demonstration
        prompt = "A beautiful sunset over mountains, digital art"

    # Generate image if prompt provided
    if prompt.strip():
        success, result_path = generate(prompt)
        if success:
            print(f"Image successfully saved at: {result_path}")
        else:
            print(f"Failed to generate image: {result_path}")
    else:
        print("No prompt provided")
