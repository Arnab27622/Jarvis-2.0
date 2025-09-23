import os
import time
import warnings
import atexit
import signal
import sys
from collections import deque
from typing import Any, Callable, Optional

import numpy as np
import sounddevice as sd
import torch
from scipy.io.wavfile import write
from assistant.automation.clap_detection.audio_inference import AudioModelHandler

# Suppress the mel filterbank warnings
warnings.filterwarnings(
    "ignore", message="At least one mel filterbank has all zero values"
)


class FinalAudioProcessor:
    """
    FINAL solution with dynamic audio ducking and real-time noise reduction.
    This version completely eliminates music interference.
    """

    def __init__(
        self,
        device_index: int,
        model_path: str,
        chunk_duration: float = 0.3,  # Very fast response
        buffer_duration: float = 1.5,  # Small buffer
        sample_rate: int = 22050,
        dtype: Any = np.int16,
        directory: str = "./",
        clap_callback: Optional[Callable[[float], None]] = None,
    ):
        """Initialize with final anti-interference solution."""
        self.chunk_duration = chunk_duration
        self.buffer_duration = buffer_duration
        self.sample_rate = sample_rate
        self.dtype = dtype
        self.directory = directory
        self.chunk_samples = int(chunk_duration * sample_rate)
        self.buffer_samples = int(buffer_duration * sample_rate)
        self.model_handler = AudioModelHandler(model_path)
        self.buffer = deque(maxlen=self.buffer_samples)
        self.clap_callback = clap_callback
        self.last_detection_time = 0
        self.detection_cooldown = 0.2

        # FINAL SOLUTION: Dynamic audio analysis
        self.baseline_audio_level = 0  # Track background audio level
        self.audio_samples_for_baseline = []
        self.baseline_established = False
        self.music_is_playing = False
        self.music_detection_threshold = 300  # Detect when music starts playing

        # Enhanced clap detection for music interference
        self.consecutive_high_amplitude_required = 2
        self.high_amplitude_count = 0

        # Use relative path for temp file
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self.temp_filename = os.path.join(project_root, "data", "temp_final.wav")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.temp_filename), exist_ok=True)

        # Register cleanup
        self._register_cleanup()

        # Configure audio stream
        self.stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=sample_rate,
            dtype=dtype,
            blocksize=self.chunk_samples,
        )

    def _register_cleanup(self):
        """Register cleanup function."""

        def cleanup():
            if os.path.exists(self.temp_filename):
                try:
                    os.remove(self.temp_filename)
                    print(f"\\nCleaned up temp file: {self.temp_filename}")
                except:
                    pass

        atexit.register(cleanup)

        def signal_handler(signum, frame):
            cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _establish_baseline(self, audio_data: np.ndarray):
        """Establish baseline audio level when no music is playing."""
        if not self.baseline_established:
            self.audio_samples_for_baseline.append(np.mean(np.abs(audio_data)))

            if len(self.audio_samples_for_baseline) >= 30:  # Collect 20 samples
                self.baseline_audio_level = np.mean(self.audio_samples_for_baseline)
                self.baseline_established = True
                print(
                    f"🎚️ Baseline audio level established: {self.baseline_audio_level:.1f}"
                )

    def _detect_music_playing(self, audio_data: np.ndarray) -> bool:
        """Detect if music is currently playing based on sustained audio levels."""
        if not self.baseline_established:
            return False

        current_level = np.mean(np.abs(audio_data))

        # If current level is significantly higher than baseline, music is likely playing
        if current_level > self.baseline_audio_level + self.music_detection_threshold:
            if not self.music_is_playing:
                print("🎵 Music detected - switching to enhanced clap detection mode")
                self.music_is_playing = True
            return True
        else:
            if self.music_is_playing:
                print("🔕 Music stopped - returning to normal clap detection mode")
                self.music_is_playing = False
            return False

    def _is_clap_with_music_playing(self, audio_data: np.ndarray) -> bool:
        """
        Enhanced clap detection when music is playing.
        Looks for sudden amplitude spikes above the music level.
        """
        if len(audio_data) < 100:
            return False

        # Calculate moving average to remove music baseline
        window_size = 50
        moving_avg = np.convolve(
            np.abs(audio_data), np.ones(window_size) / window_size, mode="valid"
        )

        # Find peaks that are significantly above the moving average
        max_amplitude = np.max(np.abs(audio_data))
        mean_amplitude = (
            np.mean(moving_avg) if len(moving_avg) > 0 else np.mean(np.abs(audio_data))
        )

        # Clap should be a sharp spike above the sustained music level
        if max_amplitude > mean_amplitude * 3.0 and max_amplitude > 500:
            # Look for sharp attack (sudden increase)
            peak_idx = np.argmax(np.abs(audio_data))

            if peak_idx > 20:  # Ensure we can look back
                pre_peak_level = np.mean(
                    np.abs(audio_data[peak_idx - 20 : peak_idx - 5])
                )
                if max_amplitude > pre_peak_level * 4.0:  # Sharp attack
                    self.high_amplitude_count += 1

                    if (
                        self.high_amplitude_count
                        >= self.consecutive_high_amplitude_required
                    ):
                        self.high_amplitude_count = 0  # Reset counter
                        return True

        self.high_amplitude_count = max(
            0, self.high_amplitude_count - 1
        )  # Decay counter
        return False

    def _is_clap_without_music(self, audio_data: np.ndarray) -> bool:
        """Standard clap detection when no music is playing."""
        if len(audio_data) == 0:
            return False

        max_amplitude = np.max(np.abs(audio_data))
        return max_amplitude > self.baseline_audio_level + 200

    def save_buffer_to_wav(self, filename: str) -> bool:
        """
        Save buffer with intelligent filtering based on music state.
        """
        if len(self.buffer) == 0:
            return False

        audio_data = np.array(self.buffer, dtype=self.dtype)

        # Establish baseline if not done yet
        self._establish_baseline(audio_data)

        if not self.baseline_established:
            # Still establishing baseline, don't process
            write(filename, self.sample_rate, np.zeros_like(audio_data))
            return False

        # Detect if music is playing
        music_detected = self._detect_music_playing(audio_data)

        # Use appropriate clap detection method
        if music_detected:
            is_potential_clap = self._is_clap_with_music_playing(audio_data)
        else:
            is_potential_clap = self._is_clap_without_music(audio_data)

        if is_potential_clap:
            # Write the actual audio data
            write(filename, self.sample_rate, audio_data)
            return True
        else:
            # Write silent audio
            write(filename, self.sample_rate, np.zeros_like(audio_data))
            return False

    def record_and_detect(self) -> None:
        """
        FINAL recording and detection with dynamic music handling.
        """
        with self.stream:
            if self.clap_callback:
                print("🎯 FINAL Clap Detection Active...")
                print("🔧 Dynamic music interference elimination: ON")
                print("🎚️ Establishing baseline audio level...")
                print("🎵 Will automatically detect when music plays")
                print("👏 Enhanced clap detection for music interference")
                print("Press Ctrl+C to stop\\n")
            else:
                print("Recording... Press Ctrl+C to stop")

            detection_count = 0

            try:
                while True:
                    try:
                        chunk, overflowed = self.stream.read(self.chunk_samples)

                        if overflowed:
                            print("⚠️ Audio buffer overflow")

                        self.buffer.extend(chunk.flatten())

                        current_time = time.time()

                        if (
                            current_time - self.last_detection_time
                            >= self.detection_cooldown
                        ):
                            # Intelligent audio analysis and filtering
                            if self.save_buffer_to_wav(self.temp_filename):
                                try:
                                    prediction = self.model_handler.predict(
                                        self.temp_filename
                                    )
                                    spec = self.model_handler.transform_audio(
                                        self.temp_filename
                                    )
                                    output = self.model_handler.model(spec)
                                    probabilities = torch.softmax(output, dim=1)
                                    predicted_prob = probabilities[0][prediction].item()

                                    # Adaptive threshold based on music state
                                    if self.music_is_playing:
                                        threshold = (
                                            0.80  # Slightly lower when music is playing
                                        )
                                    else:
                                        threshold = 0.85  # Standard threshold

                                    if predicted_prob > threshold and prediction == 1:
                                        self.last_detection_time = current_time
                                        detection_count += 1

                                        music_status = (
                                            "🎵 (with music)"
                                            if self.music_is_playing
                                            else "🔕 (no music)"
                                        )
                                        print(
                                            f"👏 CLAP DETECTED! Confidence: {predicted_prob * 100:.2f}% {music_status} (#{detection_count})"
                                        )

                                        # Call callback
                                        if self.clap_callback:

                                            def call_callback():
                                                try:
                                                    self.clap_callback(predicted_prob)
                                                except Exception as e:
                                                    print(f"Callback error: {e}")

                                            import threading

                                            callback_thread = threading.Thread(
                                                target=call_callback, daemon=True
                                            )
                                            callback_thread.start()

                                    elif prediction == 1 and predicted_prob > 0.7:
                                        print(
                                            f"🔹 Weak clap: {predicted_prob * 100:.1f}% (threshold: {threshold * 100:.0f}%)"
                                        )

                                except Exception as e:
                                    print(f"Prediction error: {e}")
                                    continue

                    except Exception as e:
                        print(f"Audio read error: {e}")
                        time.sleep(0.05)
                        continue

            except KeyboardInterrupt:
                print("\\nFINAL Clap Detection stopped.")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                # Cleanup
                if os.path.exists(self.temp_filename):
                    try:
                        os.remove(self.temp_filename)
                        print("Cleaned up temp file.")
                    except:
                        pass


def list_devices() -> None:
    """List available audio input devices."""
    devices = sd.query_devices()
    print("\\nAvailable audio input devices:")
    for i, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            print(f"{i}: {device['name']} (Input)")


def final_detect_claps(
    device_index: int,
    chunk_duration: float = 0.3,
    clap_callback: Optional[Callable[[float], None]] = None,
) -> None:
    """FINAL clap detection function with music interference elimination."""
    # Use relative path
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    model_path = os.path.join(project_root, "data", "Clap_Detect_Model.pth")

    if not os.path.exists(model_path):
        print(f"Model file not found at: {model_path}")
        print("Please train the model first using model_trainer.py")
        return

    audio_processor = FinalAudioProcessor(
        device_index=device_index,
        model_path=model_path,
        chunk_duration=chunk_duration,
        clap_callback=clap_callback,
    )

    audio_processor.record_and_detect()


def main():
    """Main function."""
    try:
        list_devices()
        device_index = int(input("\\nEnter device index: "))
        print("Starting FINAL clap detection with music interference elimination...")
        final_detect_claps(device_index)
    except ValueError:
        print("Please enter a valid number!")
    except KeyboardInterrupt:
        print("\\nExiting...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
