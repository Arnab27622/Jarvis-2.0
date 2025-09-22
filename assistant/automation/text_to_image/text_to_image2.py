# Usage warning: the api token expires every 5 minutes
# To get a new token go to https://www.decohere.ai/realtime website an create an image, click f12 and open networks tab
# check the turbo thread and open it to get the Authorization token


import time
import requests
import base64
from typing import Tuple, Optional
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

load_dotenv()

file_path = r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\images"


def validate_token() -> bool:
    """Validate the DECOHERE_AI token before making API calls"""
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
    Generates an image based on the given parameters and saves it to a file.

    Parameters:
    - prompt (str): Description of the image to generate.
    - seed (int): Seed for the image generation process.
    - width (int): Width of the generated image.
    - height (int): Height of the generated image.
    - steps (int): Number of steps for the image generation process. More the Steps More Clear and Realistic Image
    - enhance (bool): Whether to enhance the image quality.
    - safety_filter (bool): Whether to apply a safety filter to the image.

    - For Square Image Size: 768x768
    - For Portrait Image Size: 1024x576
    - For Landscape Image Size: 576x1024

    Returns:
    - Tuple[bool, Optional[str]]: A tuple containing a boolean indicating the success of the API call,
      and an optional string with the file path where the image is saved if successful.
    """

    # Validate token first
    if not validate_token():
        return False, "Token validation failed"

    if image_path is None:
        image_path = f"{file_path}/image_{int(time.time()*1000)}.jpg"

    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    token = os.getenv("DECOHERE_AI")

    # Define the URL and headers for the API call
    url = "https://turbo.decohere.ai/generate/turbo"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    # Define the payload for the POST request
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

        # Make the POST request to the API
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        base64_image_data = response.json().get("image", "")
        if not base64_image_data:
            error_msg = "No image data received in response"
            print(error_msg)
            return False, error_msg

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
    """Test function to check token validity"""
    print("Testing DECOHERE_AI token...")

    if validate_token():
        token = os.getenv("DECOHERE_AI")
        masked_token = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else token
        print(f"Token appears valid: {masked_token}")

        # Test API connectivity with a minimal request
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
    # Test token first
    test_token()
    print("\n" + "=" * 50)

    # Use input or predefined prompt
    use_input = input("Use custom prompt? (y/n): ").lower().strip()

    if use_input == "y":
        prompt = input("Enter the prompt: ")
    else:
        # Use a simple test prompt
        prompt = "A beautiful sunset over mountains, digital art"

    if prompt.strip():
        success, result_path = generate(prompt)
        if success:
            print(f"Image successfully saved at: {result_path}")
        else:
            print(f"Failed to generate image: {result_path}")
    else:
        print("No prompt provided")
