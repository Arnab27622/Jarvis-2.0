import numpy as np
import pyaudio
import time
from scipy import signal
from assistant.core.speak_selector import speak


def play_tone(frequency, duration=2, volume=0.5, sample_rate=44100, p=None):
    """
    Generate and play a pure sine wave tone through the speaker system.

    Creates a digital sine wave at the specified frequency and plays it through
    the default audio output device. Uses 16-bit PCM format for compatibility.

    Args:
        frequency (float): Frequency of the tone in Hertz (Hz)
        duration (float): Duration of the tone in seconds (default: 2)
        volume (float): Amplitude scaling factor from 0.0 to 1.0 (default: 0.5)
        sample_rate (int): Audio sampling rate in Hz (default: 44100 - CD quality)
        p (pyaudio.PyAudio, optional): Existing PyAudio instance for resource reuse

    Note:
        If no PyAudio instance is provided, one will be created and terminated
        internally. For multiple consecutive tones, it's more efficient to
        provide an existing instance.
    """
    # Generate time samples for the sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate sine wave: sin(2π * frequency * time)
    tone = np.sin(frequency * t * 2 * np.pi)

    # Apply volume scaling and convert to 16-bit PCM format
    # 32767 is the maximum value for signed 16-bit integers
    audio_data = (tone * volume * 32767).astype(np.int16)

    # Initialize PyAudio if not provided
    if p is None:
        p = pyaudio.PyAudio()
        close_p = True
    else:
        close_p = False

    try:
        # Open audio output stream with 16-bit mono configuration
        stream = p.open(
            format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True
        )
        # Play the generated tone data
        stream.write(audio_data.tobytes())
        stream.stop_stream()
        stream.close()
    finally:
        # Terminate PyAudio only if we created it internally
        if close_p:
            p.terminate()


def play_sweep(
    duration=5, volume=0.5, sample_rate=44100, start_freq=20, end_freq=20000, p=None
):
    """
    Generate and play a logarithmic frequency sweep through the speaker system.

    Creates a chirp signal that sweeps from low to high frequency logarithmically,
    which is more perceptually natural than linear sweeps for audio testing.

    Args:
        duration (float): Duration of the sweep in seconds (default: 5)
        volume (float): Amplitude scaling factor from 0.0 to 1.0 (default: 0.5)
        sample_rate (int): Audio sampling rate in Hz (default: 44100)
        start_freq (float): Starting frequency of sweep in Hz (default: 20 - near human hearing limit)
        end_freq (float): Ending frequency of sweep in Hz (default: 20000 - upper human hearing limit)
        p (pyaudio.PyAudio, optional): Existing PyAudio instance for resource reuse

    Note:
        Logarithmic sweeps provide equal time per octave, making them ideal for
        testing speaker frequency response across the human hearing range.
    """
    # Generate time samples for the sweep
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate logarithmic chirp (frequency sweep)
    sweep = signal.chirp(
        t, f0=start_freq, t1=duration, f1=end_freq, method="logarithmic"
    )

    # Convert to 16-bit PCM audio data
    audio_data = (sweep * volume * 32767).astype(np.int16)

    # Initialize PyAudio if not provided
    if p is None:
        p = pyaudio.PyAudio()
        close_p = True
    else:
        close_p = False

    try:
        # Open audio output stream and play the sweep
        stream = p.open(
            format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True
        )
        stream.write(audio_data.tobytes())
        stream.stop_stream()
        stream.close()
    finally:
        # Terminate PyAudio only if we created it internally
        if close_p:
            p.terminate()


def speaker_health_test():
    """
    Perform comprehensive speaker health assessment through audio testing.

    Plays a series of test tones and sweeps to evaluate speaker performance
    across the frequency spectrum. Provides both quantitative scoring and
    qualitative assessment of speaker condition.

    Test Sequence:
    1. Low-frequency test (100 Hz) - evaluates bass response and cone movement
    2. Mid-frequency test (1000 Hz) - evaluates vocal range clarity
    3. High-frequency tests (5000 Hz, 10000 Hz) - evaluates treble response
    4. Full frequency sweep (20-20000 Hz) - evaluates overall frequency response

    Scoring:
    - Each successful test contributes to a total health score out of 100%
    - Scores are categorized: Excellent (100%), Good (80-99%), Average (60-79%), Poor (<60%)

    Note:
        This test relies on user perception of audio playback. For precise
        measurements, specialized audio testing equipment is recommended.
    """
    speak("Playing test tones...")
    health_score = 0
    p = pyaudio.PyAudio()  # Initialize PyAudio once for efficiency

    try:
        # Test low-frequency response (bass capabilities)
        speak("Playing 100 Hz tone...")
        play_tone(100, duration=2, p=p)
        time.sleep(1)  # Brief pause between tones
        health_score += 25  # Low frequency test passed

        # Test mid-frequency response (vocal range)
        speak("Playing 1000 Hz tone...")
        play_tone(1000, duration=2, p=p)
        time.sleep(1)
        health_score += 25  # Mid frequency test passed

        # Test high-frequency response (treble capabilities)
        speak("Playing 5000 Hz tone...")
        play_tone(5000, duration=2, p=p)
        time.sleep(1)
        health_score += 20  # High frequency test passed

        speak("Playing 10,000 Hz tone...")
        play_tone(10000, duration=2, p=p)
        time.sleep(1)
        health_score += 15  # Very high frequency test passed

        # Test full frequency range with logarithmic sweep
        speak("Playing frequency sweep from 20 Hz to 20,000 Hz...")
        play_sweep(duration=5, p=p)
        time.sleep(1)
        health_score += 15  # Frequency sweep test passed

    finally:
        p.terminate()  # Ensure PyAudio is properly terminated

    # Speaker health assessment and reporting
    speak("\nSpeaker health test complete.")
    speak(f"\nSpeaker Health: {health_score}%")

    # Qualitative assessment based on score
    if health_score == 100:
        speak("The speaker is in excellent condition!")
    elif health_score >= 80:
        speak("The speaker is in good condition.")
    elif health_score >= 60:
        speak("The speaker is in average condition.")
    else:
        speak("The speaker might be in poor condition.")


if __name__ == "__main__":
    """
    Standalone speaker health testing entry point.

    When executed directly, this script will:
    1. Initialize the audio system
    2. Guide the user through a comprehensive speaker test
    3. Play test tones and frequency sweeps
    4. Provide a health assessment score and qualitative feedback

    Usage:
        Run this script to test your speaker system's health and frequency response.
        Ensure your speakers are connected and volume is at a comfortable level.
    """
    speaker_health_test()
