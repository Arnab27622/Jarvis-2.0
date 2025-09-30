"""
Ear Module - Advanced Speech Recognition System

This module provides sophisticated speech recognition capabilities using Google's Web Speech API.
It features ambient noise calibration, dynamic energy threshold adjustment, and robust error handling
for reliable voice input processing in various environments.

Key Features:
- Real-time speech recognition with continuous listening
- Adaptive ambient noise calibration
- Multiple recognition fallback strategies
- Audio debugging capabilities
- Recognition history tracking
- User activity monitoring
"""

import speech_recognition as sr
from colorama import Fore, init
import time
import wave
from collections import deque
from assistant.activities.activity_monitor import record_user_activity

# Initialize colorama for cross-platform colored terminal output
init(autoreset=True)


class AdvancedSpeechRecognizer:
    """
    Advanced speech recognition system with calibration and error handling.

    This class provides a robust interface for converting speech to text using
    Google's Web Speech API with enhanced features for reliability and accuracy.

    Attributes:
        is_listening (bool): Tracks whether the system is currently listening
        recognizer (sr.Recognizer): SpeechRecognition recognizer instance
        energy_threshold (int): Initial energy threshold for speech detection
        ambient_noise_adjusted (bool): Flag indicating if noise calibration completed
        recognition_history (deque): Circular buffer of recent recognitions for context
        calibration_duration (int): Duration in seconds for noise calibration
    """

    def __init__(self):
        """Initialize the speech recognizer with optimized settings."""
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.energy_threshold = 35100  # Initial energy threshold for speech detection
        self.ambient_noise_adjusted = False
        self.recognition_history = deque(maxlen=5)  # Keep history for context analysis

        # Configure recognizer with optimized parameters
        self.recognizer.dynamic_energy_threshold = True  # Auto-adjust to ambient noise
        self.recognizer.pause_threshold = 1.2  # Longer pause for natural speech patterns
        self.recognizer.non_speaking_duration = 0.8  # Shorter non-speaking duration
        self.recognizer.operation_timeout = None  # No operation timeout
        self.recognizer.phrase_threshold = 0.3  # Sensitivity to speech detection

        # Audio calibration settings
        self.calibration_duration = 2  # Longer calibration for better noise adjustment

    def clear_line(self):
        """
        Clear the current line in terminal output.

        Uses ANSI escape codes to clear from cursor to end of line.
        """
        print("\033[K", end="", flush=True)

    def print_listening(self):
        """
        Display listening indicator without newline.

        Shows a green 'Listening...' message that stays on the same line
        until speech is processed or timeout occurs.
        """
        if not self.is_listening:
            print(Fore.LIGHTGREEN_EX + "Listening...", end="\r", flush=True)
            self.is_listening = True

    def stop_listening_message(self):
        """
        Stop and clear the listening indicator.

        Clears the 'Listening...' message and resets the listening flag.
        """
        if self.is_listening:
            self.clear_line()
            self.is_listening = False

    def save_audio_debug(self, audio, filename="debug_audio.wav"):
        """
        Save audio data to WAV file for debugging purposes.

        Useful for troubleshooting recognition issues by analyzing
        the actual audio data that was processed.

        Args:
            audio: AudioData object from speech_recognition
            filename (str): Output filename for saved audio

        Returns:
            None
        """
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(1)  # Mono audio
                wf.setsampwidth(audio.sample_width)
                wf.setframerate(audio.sample_rate)
                wf.writeframes(audio.get_raw_data())
            print(Fore.YELLOW + f"Debug: Audio saved as {filename}")
        except Exception as e:
            print(Fore.RED + f"Error saving audio: {e}")

    def calibrate_microphone(self, source):
        """
        Perform enhanced microphone calibration with multiple attempts.

        Adjusts the recognizer for ambient noise to improve speech detection
        accuracy. Uses multiple calibration attempts for reliability.

        Args:
            source: Microphone source object

        Returns:
            None
        """
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
        """
        Use Google Web Speech API for speech recognition.

        Primary recognition method that sends audio to Google's service
        for conversion to text.

        Args:
            audio: AudioData object containing recorded speech

        Returns:
            str: Recognized text, or None if recognition failed
        """
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
        """
        Main listening function that captures and processes speech.

        Handles the complete speech recognition pipeline:
        - Microphone initialization and calibration
        - Audio capture with timeout handling
        - Speech recognition using Google Web Speech API
        - Error handling and fallback strategies
        - History tracking for contextual analysis

        Returns:
            str: Lowercase recognized text, or None if recognition failed
        """
        self.is_listening = False

        try:
            with sr.Microphone() as source:
                # Calibrate only once per session or if not calibrated
                if not self.ambient_noise_adjusted:
                    self.calibrate_microphone(source)

                print(Fore.YELLOW + "Microphone ready. Speak now...")

                # Listen with optimized parameters
                try:
                    self.print_listening()

                    # Capture audio with optimized settings
                    audio = self.recognizer.listen(
                        source,
                        timeout=5,  # Wait 5 seconds for speech to start
                        phrase_time_limit=7,  # Increased time limit for longer commands
                    )

                    self.stop_listening_message()
                    print(Fore.LIGHTYELLOW_EX + "Processing...", end="\r", flush=True)

                    # Use Google Web Speech API for recognition
                    recognized_txt = self.recognize_with_google(audio)

                    self.clear_line()
                    if recognized_txt:
                        # Add to history for context analysis
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


# Create a global instance for module-level access
recognizer = AdvancedSpeechRecognizer()


def listen():
    """
    Module-level function for easy speech recognition access.

    Provides a simplified interface to the advanced speech recognizer
    and automatically records user activity upon successful recognition.

    Returns:
        str: Recognized text in lowercase, or None if recognition failed
    """
    result = recognizer.listen()
    if result:
        record_user_activity()  # Log successful user interaction
        return result
    return None


if __name__ == "__main__":
    """
    Main execution block for testing the speech recognition system.

    Provides an interactive command-line interface for testing
    the speech recognition capabilities independently.

    Usage:
        python ear.py
        - Speak when prompted
        - Press Ctrl+C to exit
        - View recognition results and debug information
    """
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
