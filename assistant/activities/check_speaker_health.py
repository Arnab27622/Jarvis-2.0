import numpy as np
import pyaudio
import time
from scipy import signal
from assistant.core.speak_selector import speak


def play_tone(frequency, duration=2, volume=0.5, sample_rate=44100, p=None):
    """
    Plays a single tone of a specific frequency through the speaker.
    """
    # Generate samples for the sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(frequency * t * 2 * np.pi)

    # Apply volume scaling and convert to int16
    audio_data = (tone * volume * 32767).astype(np.int16)

    # Initialize PyAudio if not provided
    if p is None:
        p = pyaudio.PyAudio()
        close_p = True
    else:
        close_p = False

    try:
        # Open stream
        stream = p.open(
            format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True
        )
        # Play the tone
        stream.write(audio_data.tobytes())
        stream.stop_stream()
        stream.close()
    finally:
        if close_p:
            p.terminate()


def play_sweep(
    duration=5, volume=0.5, sample_rate=44100, start_freq=20, end_freq=20000, p=None
):
    """
    Plays a frequency sweep from start_freq to end_freq through the speaker.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Use logarithmic sweep with non-zero start frequency
    sweep = signal.chirp(
        t, f0=start_freq, t1=duration, f1=end_freq, method="logarithmic"
    )

    # Convert to int16 audio data
    audio_data = (sweep * volume * 32767).astype(np.int16)

    # Initialize PyAudio if not provided
    if p is None:
        p = pyaudio.PyAudio()
        close_p = True
    else:
        close_p = False

    try:
        # Open stream and play sweep
        stream = p.open(
            format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True
        )
        stream.write(audio_data.tobytes())
        stream.stop_stream()
        stream.close()
    finally:
        if close_p:
            p.terminate()


def speaker_health_test():
    """
    Plays different tones and sweeps to test the speaker's health.
    """
    speak("Playing test tones...")
    health_score = 0
    p = pyaudio.PyAudio()  # Initialize PyAudio once

    try:
        # Test low-frequency tone
        speak("Playing 100 Hz tone...")
        play_tone(100, duration=2, p=p)
        time.sleep(1)
        health_score += 25

        # Test mid-frequency tone
        speak("Playing 1000 Hz tone...")
        play_tone(1000, duration=2, p=p)
        time.sleep(1)
        health_score += 25

        # Test high-frequency tones
        speak("Playing 5000 Hz tone...")
        play_tone(5000, duration=2, p=p)
        time.sleep(1)
        health_score += 20

        speak("Playing 10,000 Hz tone...")
        play_tone(10000, duration=2, p=p)
        time.sleep(1)
        health_score += 15

        # Frequency sweep test
        speak("Playing frequency sweep from 20 Hz to 20,000 Hz...")
        play_sweep(duration=5, p=p)
        time.sleep(1)
        health_score += 15

    finally:
        p.terminate()  # Ensure PyAudio is terminated

    # Speaker health assessment
    speak("\nSpeaker health test complete.")
    speak(f"\nSpeaker Health: {health_score}%")

    if health_score == 100:
        speak("The speaker is in excellent condition!")
    elif health_score >= 80:
        speak("The speaker is in good condition.")
    elif health_score >= 60:
        speak("The speaker is in average condition.")
    else:
        speak("The speaker might be in poor condition.")


if __name__ == "__main__":
    speaker_health_test()
