import base64
import requests
import os
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

load_dotenv()


def generate_image_from_text(prompt_text):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    body = {
        "steps": 40,
        "width": 1024,
        "height": 1024,
        "seed": 0,
        "cfg_scale": 5,
        "samples": 1,
        "text_prompts": [
            {"text": prompt_text, "weight": 1},
            {"text": "blurry, bad", "weight": -1},
        ],
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}",
    }

    response = requests.post(
        url,
        headers=headers,
        json=body,
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()

    folder_path = r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\images"
    os.makedirs(folder_path, exist_ok=True)

    # Save the generated image(s)
    for i, image in enumerate(data["artifacts"]):
        filename = f'{folder_path}/txt2img_{image["seed"]}.png'
        with open(filename, "wb") as f:
            f.write(base64.b64decode(image["base64"]))
        speak(f"Image saved in Images folder.")


if __name__ == "__main__":
    user_prompt = input("Enter the text prompt for the image generation: ")
    generate_image_from_text(user_prompt)
