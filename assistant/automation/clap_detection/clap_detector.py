"""
Module for real-time clap detection using audio stream analysis and machine learning.
"""

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

warnings.filterwarnings("ignore")


class FinalAudioProcessor:
    """
    Handles real-time audio stream processing, signal filtering, and clap inference.
    """

    def __init__(
        self,
        device_index: int,
        model_path: str,
        chunk_duration: float = 0.5,
        buffer_duration: float = 2.0,
        sample_rate: int = 22050,
        dtype: Any = np.int16,
        directory: str = "./",
        clap_callback: Optional[Callable[[float], None]] = None,
    ):
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
        self.detection_cooldown = 1.0

        self.baseline_level = None
        self.baseline_samples = deque(maxlen=50)
        self.min_clap_amplitude = 500

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self.temp_filename = os.path.join(project_root, "data", "temp_clap.wav")
        os.makedirs(os.path.dirname(self.temp_filename), exist_ok=True)

        self._register_cleanup()

        self.stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=sample_rate,
            dtype=dtype,
            blocksize=self.chunk_samples,
        )

    def _register_cleanup(self):
        """Registers system signal handlers and exit hooks for resource cleanup."""

        def cleanup():
            if os.path.exists(self.temp_filename):
                try:
                    os.remove(self.temp_filename)
                except:
                    pass

        atexit.register(cleanup)

        def signal_handler(signum, frame):
            cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _update_baseline(self, audio_data: np.ndarray):
        """Updates the rolling median of audio levels to adapt to background noise."""
        current_level = np.mean(np.abs(audio_data))
        self.baseline_samples.append(current_level)

        if len(self.baseline_samples) >= 10:
            self.baseline_level = np.median(self.baseline_samples)

    def _is_potential_clap(self, audio_data: np.ndarray) -> bool:
        """Analyzes audio signal for amplitude spikes and sharp attack characteristics."""
        if len(audio_data) == 0 or self.baseline_level is None:
            return False

        max_amplitude = np.max(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data**2))

        if max_amplitude < self.min_clap_amplitude:
            return False

        if max_amplitude < self.baseline_level * 3:
            return False

        if len(audio_data) > 100:
            peak_idx = np.argmax(np.abs(audio_data))

            if peak_idx > 50:
                pre_peak_rms = np.sqrt(
                    np.mean(audio_data[peak_idx - 50 : peak_idx - 10] ** 2)
                )
                peak_rms = np.sqrt(
                    np.mean(audio_data[peak_idx - 10 : peak_idx + 10] ** 2)
                )

                if peak_rms > pre_peak_rms * 2:
                    return True

        return False

    def enable_debug_mode(self):
        """Enables verbose logging for audio analysis."""
        self.debug = True

    def record_and_detect_debug(self) -> None:
        """Runs the detection loop with detailed console output for debugging."""
        with self.stream:
            print("🐛 DEBUG MODE: Clap Detection with Detailed Audio Analysis")
            print("=" * 50)

            detection_count = 0
            frame_count = 0

            try:
                while True:
                    try:
                        chunk, overflowed = self.stream.read(self.chunk_samples)
                        if overflowed:
                            print("⚠️ Audio buffer overflow")

                        self.buffer.extend(chunk.flatten())
                        frame_count += 1

                        audio_data = np.array(chunk.flatten())
                        max_amp = np.max(np.abs(audio_data))
                        rms = np.sqrt(np.mean(audio_data**2))

                        self._update_baseline(audio_data)

                        if frame_count % 50 == 0:
                            baseline_info = (
                                f"{self.baseline_level:.1f}"
                                if self.baseline_level
                                else "Calculating..."
                            )
                            print(
                                f"📊 Frame {frame_count}: MaxAmp={max_amp:6.1f}, RMS={rms:6.1f}, Baseline={baseline_info}"
                            )

                        current_time = time.time()

                        if (
                            current_time - self.last_detection_time
                            >= self.detection_cooldown
                        ):
                            if self.save_buffer_to_wav(self.temp_filename):
                                try:
                                    prediction, confidence, probabilities = (
                                        self.model_handler.predict(
                                            self.temp_filename, confidence_threshold=0.7
                                        )
                                    )

                                    print(
                                        f"🔍 Model Analysis: Pred={prediction}, Conf={confidence:.3f}, Probs=[Noise: {probabilities[0]:.3f}, Clap: {probabilities[1]:.3f}]"
                                    )

                                    if prediction == 1 and confidence > 0.85:
                                        self.last_detection_time = current_time
                                        detection_count += 1
                                        print(
                                            f"🎉 CLAP DETECTED! Confidence: {confidence:.3f} (#{detection_count})"
                                        )

                                        if self.clap_callback:
                                            try:
                                                self.clap_callback(confidence)
                                            except Exception as e:
                                                print(f"Callback error: {e}")

                                    elif prediction == 1:
                                        print(
                                            f"❓ Weak clap signal: {confidence:.3f} (needs >0.85)"
                                        )

                                except Exception as e:
                                    print(f"❌ Prediction error: {e}")

                    except Exception as e:
                        print(f"❌ Audio processing error: {e}")
                        time.sleep(0.1)

            except KeyboardInterrupt:
                print(
                    f"\n🛑 Debug mode stopped. Processed {frame_count} frames, detected {detection_count} claps."
                )

    def save_buffer_to_wav(self, filename: str) -> bool:
        """Writes the current audio buffer to a temporary WAV file for inference."""
        if len(self.buffer) < self.chunk_samples:
            return False

        audio_data = np.array(self.buffer, dtype=self.dtype)

        self._update_baseline(audio_data)

        if self._is_potential_clap(audio_data):
            write(filename, self.sample_rate, audio_data)
            return True
        else:
            write(filename, self.sample_rate, np.zeros(1000, dtype=self.dtype))
            return False

    def record_and_detect(self) -> None:
        """Main execution loop for continuous audio monitoring and clap detection."""
        with self.stream:
            print("🎯 Clap Detection Active...")
            print("🔧 Improved audio processing: ON")
            print("📊 Establishing baseline audio level...")
            print("👏 Confidence-based clap detection")
            print("Press Ctrl+C to stop\n")

            detection_count = 0
            consecutive_detections = 0

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
                            if self.save_buffer_to_wav(self.temp_filename):
                                try:
                                    prediction, confidence, probabilities = (
                                        self.model_handler.predict(
                                            self.temp_filename, confidence_threshold=0.7
                                        )
                                    )

                                    if prediction == 1 and confidence > 0.85:
                                        self.last_detection_time = current_time
                                        detection_count += 1
                                        consecutive_detections += 1

                                        print(
                                            f"👏 CLAP DETECTED! Confidence: {confidence:.3f} (#{detection_count})"
                                        )

                                        consecutive_detections = 0

                                        if self.clap_callback:
                                            try:
                                                self.clap_callback(confidence)
                                            except Exception as e:
                                                print(f"Callback error: {e}")

                                    elif prediction == 1 and confidence > 0.6:
                                        print(
                                            f"🔹 Weak signal: {confidence:.3f} (needs {0.85-confidence:.3f} more)"
                                        )
                                    else:
                                        if consecutive_detections > 0:
                                            consecutive_detections = 0

                                except Exception as e:
                                    print(f"Prediction error: {e}")
                                    continue

                    except Exception as e:
                        print(f"Audio processing error: {e}")
                        time.sleep(0.1)
                        continue

            except KeyboardInterrupt:
                print("\n🛑 Clap Detection stopped.")
            except Exception as e:
                print(f"Unexpected error: {e}")
            finally:
                if os.path.exists(self.temp_filename):
                    try:
                        os.remove(self.temp_filename)
                    except:
                        pass


def list_devices() -> None:
    """Prints a list of all available audio input devices."""
    devices = sd.query_devices()
    print("\nAvailable audio input devices:")
    for i, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            print(f"{i}: {device['name']} (Input)")


def final_detect_claps(
    device_index: int,
    chunk_duration: float = 0.5,
    clap_callback: Optional[Callable[[float], None]] = None,
) -> None:
    """Initializes and starts the clap detection process."""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    model_path = os.path.join(project_root, "data", "Clap_Detect_Model.pth")

    if not os.path.exists(model_path):
        print(f"❌ Model file not found at: {model_path}")
        print("Please train the model first using model_trainer.py")
        return

    audio_processor = FinalAudioProcessor(
        device_index=device_index,
        model_path=model_path,
        chunk_duration=chunk_duration,
        clap_callback=clap_callback,
    )

    audio_processor.record_and_detect()


def main() -> None:
    """Entry point for the clap detection CLI."""
    try:
        list_devices()
        device_index = int(input("\nEnter device index: "))
        print("Starting improved clap detection...")
        final_detect_claps(device_index)
    except ValueError:
        print("❌ Please enter a valid number!")
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
