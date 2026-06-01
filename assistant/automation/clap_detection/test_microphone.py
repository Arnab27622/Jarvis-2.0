"""
Module for diagnosing microphone hardware and testing audio input capabilities,
specifically tailored for clap detection applications.
"""

import sounddevice as sd
import numpy as np
import time
import wave


from typing import Optional, List, Tuple, Any

def test_microphone(device_index: Optional[int] = None, duration: int = 5, sample_rate: int = 22050) -> bool:
    """
    Records audio from the specified device and analyzes it for signal presence.
    Returns True if audio amplitude exceeds the silence threshold.
    """

    print("🎤 Testing Microphone...")
    print("Recording for 5 seconds... Speak or make some noise!")

    try:
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device_index,
        )
        sd.wait()

        print("Recording complete!")

        audio_data = recording.flatten()

        max_amplitude = np.max(np.abs(audio_data))
        rms_amplitude = np.sqrt(np.mean(audio_data**2))
        silence_threshold = 100

        print("📊 Audio Analysis:")
        print(f"   Max Amplitude: {max_amplitude}")
        print(f"   RMS Amplitude: {rms_amplitude:.2f}")
        print(f"   Silence Threshold: {silence_threshold}")

        if max_amplitude < silence_threshold:
            print("❌ MICROPHONE ISSUE: No significant audio detected!")
            print("   Check if:")
            print("   - Microphone is connected")
            print("   - Microphone is not muted")
            print("   - Correct device is selected")
            print("   - Microphone permissions are granted")
        else:
            print("✅ Microphone is working!")

        filename = "test_recording.wav"
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        print(f"💾 Test recording saved as: {filename}")

        return max_amplitude > silence_threshold

    except Exception as e:
        print(f"❌ Error during recording: {e}")
        return False


def list_audio_devices() -> List[Tuple[int, Any]]:
    """
    Queries and displays all available audio input devices.
    Returns a list of tuples containing device index and device info.
    """
    print("\n🔊 Available Audio Devices:")
    devices = sd.query_devices()

    input_devices = []
    for i, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            input_devices.append((i, device))
            print(
                f"   Input {i}: {device['name']} (Input channels: {device['max_input_channels']})"
            )

    return input_devices


def real_time_mic_monitor(device_index: Optional[int] = None, duration: int = 10) -> None:
    """
    Streams audio from the microphone and displays a visual volume meter in the console.
    """
    print("\n📈 Real-time Microphone Monitoring (10 seconds)...")
    print("Watch the levels as you speak or make noise:")

    start_time = time.time()
    try:

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")

            current_level = np.max(np.abs(indata))
            # Create a simple level meter
            bars = int(current_level / 1000)  # Scale for visualization
            level_bar = "[" + "#" * min(bars, 20) + " " * (20 - min(bars, 20)) + "]"
            print(f"Level: {level_bar} {current_level:6.0f}", end="\r")

        with sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=22050,
            callback=audio_callback,
            blocksize=1024,
        ):
            while time.time() - start_time < duration:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"\nError during monitoring: {e}")


def test_clap_detection_hardware(device_index: Optional[int] = None) -> bool:
    """
    Performs a sequence of tests to verify if the hardware is suitable for clap detection.
    """
    print("\n👏 Testing Clap Detection Hardware Setup...")

    mic_working = test_microphone(device_index, duration=3)

    if not mic_working:
        print("❌ Cannot proceed - microphone not working")
        return False

    print("\n🔊 Make 3 loud claps near the microphone...")
    real_time_mic_monitor(device_index, duration=10)

    print("\n🎯 Recording clap test...")
    recording = sd.rec(
        int(5 * 22050), samplerate=22050, channels=1, dtype="int16", device=device_index
    )

    print("Make 2-3 distinct claps now...")
    sd.wait()

    audio_data = recording.flatten()
    clap_threshold = 5000

    peaks = np.where(np.abs(audio_data) > clap_threshold)[0]

    if len(peaks) > 0:
        print(f"✅ Detected {len(np.unique(peaks // 1000))} potential clap events!")
        print(f"   Maximum clap amplitude: {np.max(np.abs(audio_data))}")
    else:
        print(f"❌ No claps detected above threshold {clap_threshold}")
        print("   Try:")
        print("   - Clapping louder")
        print("   - Moving closer to microphone")
        print("   - Increasing microphone sensitivity in system settings")

    return len(peaks) > 0


if __name__ == "__main__":
    """
    Main entry point for the diagnostic tool.
    """
    print("🔍 Audio Hardware Diagnostic Tool")
    print("=" * 40)

    input_devices = list_audio_devices()

    if not input_devices:
        print("❌ No input devices found!")
        exit(1)

    try:
        device_index = int(input("\nEnter device index to test: "))

        test_clap_detection_hardware(device_index)

    except ValueError:
        print("❌ Please enter a valid number!")
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
