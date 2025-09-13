import asyncio
import os
import edge_tts
import pygame
import tempfile
import sys
import time
import threading

VOICE = "en-AU-WilliamNeural"

pygame.init()
pygame.mixer.init()


def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.055)
    print()


async def stream_audio(text, voice):
    """Stream audio directly without storing the entire file in memory"""
    communicate = edge_tts.Communicate(text, voice)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name

    try:
        await communicate.save(tmp_path)
        return tmp_path
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise e


def play_audio_file(file_path):
    """Play audio from file and then clean up"""
    try:
        sound = pygame.mixer.Sound(file_path)
        sound.play()

        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Error playing audio: {e}")
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)


async def speak_async(text):
    """Async function to generate and play audio with minimal memory usage"""
    try:
        # Generate audio file first
        audio_file_path = await stream_audio(text, VOICE)
        
        # Create and start a thread for animated printing
        print_thread = threading.Thread(target=print_animated_message, args=(text,))
        print_thread.start()
        
        # Play audio in the main thread (this will block until audio finishes)
        play_audio_file(audio_file_path)
        
        # Wait for the printing thread to finish
        print_thread.join()

    except Exception as e:
        print(f"Error in text-to-speech: {e}")


def speak(text):
    """Main function to speak text with minimal memory usage"""
    time.sleep(0.1)
    asyncio.run(speak_async(text))


if __name__ == "__main__":
    speak("hello, how are you?")