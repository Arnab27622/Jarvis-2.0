from typing import Optional
from assistant.core.speak_selector import speak

from assistant.automation.text_to_image.text_to_image import generate_image_from_text as gen_stability
from assistant.automation.text_to_image.text_to_image2 import generate as gen_cloudflare
from assistant.automation.text_to_image.text_to_image3 import generate_image_from_text as gen_pollinations

class ImageManager:
    """
    Manager for handling Text-to-Image generation requests.
    Routes prompts to specific engines based on user preference, or falls back sequentially
    to ensure high reliability.
    """

    def __init__(self):
        # Default fallback order: Pollinations -> Cloudflare -> Stability
        self.fallback_order = [
            ("pollinations", self._run_pollinations),
            ("cloudflare", self._run_cloudflare),
            ("stability", self._run_stability)
        ]

    def _run_stability(self, prompt: str) -> Optional[str]:
        print("[ImageManager] Attempting generation with Stability AI...")
        res = gen_stability(prompt)
        # Returns path if successful, otherwise None
        return res

    def _run_cloudflare(self, prompt: str) -> Optional[str]:
        print("[ImageManager] Attempting generation with Cloudflare Flux...")
        success, path = gen_cloudflare(prompt)
        return path if success else None

    def _run_pollinations(self, prompt: str) -> Optional[str]:
        print("[ImageManager] Attempting generation with Pollinations Flux...")
        res = gen_pollinations(prompt)
        # Returns path if successful, otherwise None
        return res

    def generate_image(self, prompt: str, preferred_engine: Optional[str] = None) -> Optional[str]:
        """
        Attempts to generate an image using the preferred engine if specified.
        If it fails, or if no engine is specified, runs through the fallback chain.
        """
        prompt = prompt.strip()
        
        # 1. Try preferred engine if specified
        if preferred_engine:
            engine_name = preferred_engine.lower()
            print(f"[ImageManager] User explicitly requested engine: {engine_name}")
            
            if "stability" in engine_name:
                res = self._run_stability(prompt)
                if res: return res
                print("[ImageManager] Stability AI failed. Falling back...")
            
            elif "cloudflare" in engine_name:
                res = self._run_cloudflare(prompt)
                if res: return res
                print("[ImageManager] Cloudflare failed. Falling back...")
                
            elif "pollination" in engine_name:
                res = self._run_pollinations(prompt)
                if res: return res
                print("[ImageManager] Pollinations failed. Falling back...")
        
        # 2. Run sequential fallback chain
        print("[ImageManager] Starting sequential fallback chain...")
        for name, func in self.fallback_order:
            # Skip the one we already tried above
            if preferred_engine and name in preferred_engine.lower():
                continue
                
            res = func(prompt)
            if res:
                print(f"[ImageManager] Successfully generated image using {name.capitalize()}.")
                return res
                
            print(f"[ImageManager] Engine {name} failed, trying next...")

        # 3. All engines failed
        speak("I'm sorry, but all of my image generation modules are currently unavailable.")
        return None

# Singleton instance
image_manager = ImageManager()

def generate_image(prompt: str, engine: Optional[str] = None) -> Optional[str]:
    """Consolidated entry point for image generation."""
    return image_manager.generate_image(prompt, engine)

if __name__ == "__main__":
    # Test
    generate_image("A futuristic city", "cloudflare")


# --- Command Handlers ---
from assistant.core.registry import on_regex

@on_regex(r"(?:please\s+)?(?:create|generate)(?:\s+an)?\s+image\s+of\s+(?P<prompt>.*?)(?:\s+using\s+(?P<engine>cloudflare|stability|pollination.*))?$")
def handle_image_gen(prompt, engine=None):
    speak("Generating the image. Please wait a moment...")
    path = generate_image(prompt, engine)
    
    import os
    if path:
        filename = os.path.basename(path)
        # Speak the message and pass the relative URL for the UI
        speak("Image generation successful.", image=f"/images/{filename}")

