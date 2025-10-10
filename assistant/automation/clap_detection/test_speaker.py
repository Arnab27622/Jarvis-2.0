import sounddevice as sd
import numpy as np
import time


def test_speaker(device_index=None):
    """Test speaker functionality"""
    print("🔊 Testing Speaker...")

    # Generate test tones
    sample_rate = 22050
    duration = 2

    # Low frequency tone
    print("Playing low tone (250Hz)...")
    t = np.linspace(0, duration, int(sample_rate * duration))
    tone_low = 0.3 * np.sin(2 * np.pi * 250 * t)
    sd.play(tone_low, sample_rate, device=device_index)
    sd.wait()

    time.sleep(0.5)

    # High frequency tone
    print("Playing high tone (1000Hz)...")
    tone_high = 0.3 * np.sin(2 * np.pi * 1000 * t)
    sd.play(tone_high, sample_rate, device=device_index)
    sd.wait()

    print("✅ Speaker test complete!")
    print("   You should have heard two different tones.")


if __name__ == "__main__":
    devices = sd.query_devices()
    print("Available output devices:")
    for i, device in enumerate(devices):
        if device["max_output_channels"] > 0:
            print(f"  {i}: {device['name']}")

    try:
        device_index = int(input("Enter output device index: "))
        test_speaker(device_index)
    except Exception as e:
        print(f"Error: {e}")
