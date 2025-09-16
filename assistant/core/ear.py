from pathlib import Path
import sys
import speech_recognition as sr
from colorama import Fore, init
import time
import wave
from collections import deque


current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))
from assistant.activities.activity_monitor import record_user_activity

init(autoreset=True)


class AdvancedSpeechRecognizer:
    def __init__(self):
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.energy_threshold = 35100  # Initial energy threshold
        self.ambient_noise_adjusted = False
        self.recognition_history = deque(maxlen=5)  # Keep history for context

        # Optimize recognizer settings
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.2  # Longer pause for natural speech
        self.recognizer.non_speaking_duration = 0.8  # Shorter non-speaking duration
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.3  # Sensitivity to speech detection

        # Audio calibration values
        self.calibration_duration = 2  # Longer calibration for better noise adjustment

    def clear_line(self):
        """Clear the current line in terminal"""
        print("\033[K", end="", flush=True)

    def print_listening(self):
        """Print listening message without newline"""
        if not self.is_listening:
            print(Fore.LIGHTGREEN_EX + "Listening...", end="\r", flush=True)
            self.is_listening = True

    def stop_listening_message(self):
        """Stop and clear the listening message"""
        if self.is_listening:
            self.clear_line()
            self.is_listening = False

    def save_audio_debug(self, audio, filename="debug_audio.wav"):
        """Save audio data for debugging purposes"""
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(audio.sample_width)
                wf.setframerate(audio.sample_rate)
                wf.writeframes(audio.get_raw_data())
            print(Fore.YELLOW + f"Debug: Audio saved as {filename}")
        except Exception as e:
            print(Fore.RED + f"Error saving audio: {e}")

    def calibrate_microphone(self, source):
        """Enhanced calibration with multiple attempts"""
        print(Fore.YELLOW + "Calibrating microphone for ambient noise...")

        # Multiple calibration attempts for better accuracy
        for attempt in range(3):
            try:
                self.recognizer.adjust_for_ambient_noise(
                    source, duration=self.calibration_duration
                )
                print(Fore.YELLOW + f"Calibration attempt {attempt+1}/3 successful")
                self.ambient_noise_adjusted = True

                # Set a reasonable energy threshold based on calibration
                if self.recognizer.energy_threshold < 100:
                    self.recognizer.energy_threshold = 300
                break
            except Exception as e:
                print(Fore.RED + f"Calibration attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    print(Fore.YELLOW + "Using default energy threshold")
                    self.recognizer.energy_threshold = 300

    def recognize_with_google(self, audio):
        """Use Google Web Speech API for recognition"""
        recognized_text = None

        # Try Google Web Speech API
        try:
            recognized_text = self.recognizer.recognize_google(audio, language="en-US")
            print(Fore.GREEN + "Google Web Speech recognition successful")
            return recognized_text
        except sr.UnknownValueError:
            print(Fore.YELLOW + "Google Web Speech could not understand audio")
        except sr.RequestError as e:
            print(Fore.YELLOW + f"Google Web Speech request error: {e}")

        return recognized_text

    def listen(self):
        self.is_listening = False

        try:
            with sr.Microphone() as source:
                # Calibrate only once per session or if not calibrated
                if not self.ambient_noise_adjusted:
                    self.calibrate_microphone(source)

                print(Fore.YELLOW + "Microphone ready. Speak now...")

                # Listen with longer timeout and phrase limit
                try:
                    self.print_listening()

                    # Listen with optimized parameters
                    audio = self.recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=7,  # Increased time limit for longer commands
                    )

                    self.stop_listening_message()
                    print(Fore.LIGHTYELLOW_EX + "Processing...", end="\r", flush=True)

                    # Use Google Web Speech API for recognition
                    recognized_txt = self.recognize_with_google(audio)

                    self.clear_line()
                    if recognized_txt:
                        # Add to history for context
                        self.recognition_history.append(recognized_txt)

                        print(Fore.BLUE + "You said: " + Fore.CYAN + recognized_txt)
                        return recognized_txt.lower()
                    else:
                        print(Fore.RED + "Couldn't understand the audio")
                        return None

                except sr.WaitTimeoutError:
                    self.stop_listening_message()
                    self.clear_line()
                    print(Fore.YELLOW + "Listening timeout - no speech detected")
                    return None
                except sr.UnknownValueError:
                    self.stop_listening_message()
                    self.clear_line()
                    print(Fore.RED + "Didn't catch that", end="\r", flush=True)
                    time.sleep(1.0)
                    self.clear_line()
                    return None
                except sr.RequestError as e:
                    self.stop_listening_message()
                    self.clear_line()
                    print(Fore.RED + f"Recognition service error: {e}")
                    return None
                except Exception as e:
                    self.stop_listening_message()
                    self.clear_line()
                    print(Fore.RED + f"Error: {e}")
                    # Save audio for debugging if recognition fails consistently
                    self.save_audio_debug(audio)
                    return None

        except OSError as e:
            print(Fore.RED + f"Microphone error: {e}")
            return None
        except Exception as e:
            print(Fore.RED + f"Unexpected error: {e}")
            return None


# Create a global instance
recognizer = AdvancedSpeechRecognizer()


# Define the listen function that will be imported
def listen():
    result = recognizer.listen()
    if result:
        record_user_activity()  # Add this line
        return result
    return None


if __name__ == "__main__":
    asr = AdvancedSpeechRecognizer()

    try:
        print(Fore.CYAN + "Advanced Speech Recognition initialized!")
        print(Fore.CYAN + "Press Ctrl+C to exit\n")

        while True:
            result = asr.listen()
            if result:
                print(Fore.GREEN + f"Recognized: {result}")
                # Add your command processing logic here

    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nProgram terminated by user.")
