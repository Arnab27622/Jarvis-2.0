import os
import time
import warnings
from collections import deque
from typing import Any
import numpy as np
import sounddevice as sd
import torch
from scipy.io.wavfile import write
from assistant.automation.clap_detection.audio_inference import AudioModelHandler

# Suppress the mel filterbank warnings
warnings.filterwarnings(
    "ignore", message="At least one mel filterbank has all zero values"
)


class AudioProcessor:
    """
    Class for processing and detecting claps in audio input.
    """

    def __init__(
        self,
        device_index: int,
        model_path: str,
        chunk_duration: float = 1.0,  # Increased from 0.5 to 1.0 for better detection
        buffer_duration: float = 3,  # Reduced from 10 to 3 seconds
        sample_rate: int = 22050,  # Reduced from 44100 to 22050
        dtype: Any = np.int16,
        directory: str = "./",
    ):
        """
        Initializes the AudioProcessor.
        """
        self.chunk_duration = chunk_duration
        self.buffer_duration = buffer_duration
        self.sample_rate = sample_rate
        self.dtype = dtype
        self.directory = directory

        self.chunk_samples = int(chunk_duration * sample_rate)
        self.buffer_samples = int(buffer_duration * sample_rate)

        self.model_handler = AudioModelHandler(model_path)
        self.buffer = deque(maxlen=self.buffer_samples)

        # Use relative path for temp file
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self.temp_filename = os.path.join(project_root, "data", "temp.wav")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.temp_filename), exist_ok=True)

        self.stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=sample_rate,
            dtype=dtype,
            blocksize=self.chunk_samples,
        )

    def save_buffer_to_wav(self, filename: str) -> None:
        """
        Saves the current buffer to a WAV file.
        """
        if len(self.buffer) > 0:
            audio_data = np.array(self.buffer, dtype=self.dtype)
            # Ensure the audio data is not empty and has reasonable amplitude
            if np.max(np.abs(audio_data)) > 100:  # Basic silence detection threshold
                write(filename, self.sample_rate, audio_data)
            else:
                # Write silent audio if buffer is too quiet
                write(filename, self.sample_rate, np.zeros_like(audio_data))

    def record_and_detect(self) -> None:
        """
        Records audio input and detects claps.
        """
        with self.stream:
            print("Recording... Press Ctrl+C to stop")
            try:
                while True:
                    chunk, overflowed = self.stream.read(self.chunk_samples)
                    if overflowed:
                        print("Audio buffer overflowed!")

                    self.buffer.extend(chunk.flatten())

                    # Save and analyze
                    self.save_buffer_to_wav(self.temp_filename)

                    try:
                        prediction = self.model_handler.predict(self.temp_filename)
                        spec = self.model_handler.transform_audio(self.temp_filename)
                        output = self.model_handler.model(spec)
                        probabilities = torch.softmax(output, dim=1)
                        predicted_prob = probabilities[0][prediction].item()


                        if predicted_prob > 0.85 and prediction == 1:
                            print(
                                f"👏 CLAP DETECTED! Confidence: {predicted_prob * 100:.2f}%"
                            )
                            # Optional: Add a cooldown period
                            time.sleep(0.5)
                        # elif prediction == 1:
                        #     print(f"Clap: ({predicted_prob * 100:.2f}%)")
                        else:
                            print(f"- Noise ({predicted_prob * 100:.2f}%)")

                    except Exception as e:
                        print(f"Error in prediction: {e}")
                        continue

                    # No need for extra sleep since read() blocks

            except KeyboardInterrupt:
                print("\nRecording stopped by user.")
            except Exception as e:
                print(f"Error: {e}")


def list_devices() -> None:
    """
    Lists available audio input devices.
    """
    devices = sd.query_devices()
    print("\nAvailable audio input devices:")
    for i, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            print(f"{i}: {device['name']} (Input)")


def detect_claps(device_index: int, chunk_duration: float = 1.0) -> None:
    """
    Detects claps using audio input from the specified device.
    """
    # Use relative path
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    model_path = os.path.join(project_root, "data", "Clap_Detect_Model.pth")

    if not os.path.exists(model_path):
        print(f"Model file not found at: {model_path}")
        print("Please train the model first using model_trainer.py")
        return

    audio_processor = AudioProcessor(
        device_index=device_index,
        model_path=model_path,
        chunk_duration=chunk_duration,
    )
    audio_processor.record_and_detect()


if __name__ == "__main__":
    list_devices()
    try:
        device_index = int(
            input("\nEnter the index of the input device you want to use: ")
        )
        print("Starting clap detection...")
        detect_claps(device_index)
    except ValueError:
        print("Please enter a valid number!")
    except KeyboardInterrupt:
        print("\nExiting...")
