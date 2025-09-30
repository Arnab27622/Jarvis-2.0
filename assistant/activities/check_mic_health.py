import pyaudio
import numpy as np
import time
from assistant.core.speak_selector import speak


def list_input_devices():
    """
    List all available audio input devices on the system.

    Uses PyAudio to enumerate all audio devices and filters for those with
    input capabilities. Provides voice feedback listing each available device.

    Returns:
        list: A list of tuples containing (device_index, device_name) for each input device
    """
    audio = pyaudio.PyAudio()
    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get("deviceCount")
    devices = []

    speak("Available input devices:")
    for i in range(0, numdevices):
        device_info = audio.get_device_info_by_host_api_device_index(0, i)
        if device_info.get("maxInputChannels") > 0:
            devices.append((i, device_info.get("name")))
            speak(f"{i}: {device_info.get('name')}")

    audio.terminate()
    return devices


def get_mic_health(seconds=5, threshold_multiplier=3.0, device_index=None):
    """
    Perform comprehensive microphone health analysis.

    Records audio from the specified microphone and analyzes multiple quality metrics:
    - Audio activity detection
    - Signal-to-noise ratio (SNR)
    - Clipping detection (distortion)
    - Frequency response analysis
    - Dynamic noise floor estimation

    Args:
        seconds (int): Duration of recording for analysis (default: 5)
        threshold_multiplier (float): Multiplier for dynamic noise threshold (default: 3.0)
        device_index (int, optional): Specific device index to test. Uses default if None.

    Returns:
        dict or None: Dictionary containing health metrics if successful, None if failed.
                      Metrics include:
                      - Microphone Health (%): Percentage of time audio activity detected
                      - Average Signal-to-Noise Ratio (dB): Quality of signal vs background noise
                      - Clipping Percentage (%): Percentage of audio that was distorted
                      - Frequency Range Coverage (%): How well frequency spectrum is captured
                      - Noise Floor: Estimated background noise level
    """
    # Audio stream configuration constants
    CHUNK = 1024  # Audio chunk size (samples per buffer)
    FORMAT = pyaudio.paInt16  # 16-bit resolution
    CHANNELS = 1  # Mono audio
    RATE = 44100  # Sampling rate (Hz) - CD quality

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # If no device index is provided, use the default input device
    if device_index is None:
        try:
            default_device_info = audio.get_default_input_device_info()
            device_index = default_device_info["index"]
            speak(f"Using default input device: {default_device_info['name']}")
        except:
            speak("Error getting default input device, using first available")
            device_index = 0

    try:
        # Open the audio stream with explicit device index
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK,
        )
    except Exception as e:
        print(f"Error opening stream: {e}")
        audio.terminate()
        return None

    speak(f"Recording for {seconds} seconds...")
    time.sleep(1)  # Small pause before recording to stabilize

    # Initialize analysis variables
    sound_count = 0  # Count of chunks with detected sound
    total_chunks = int(RATE / CHUNK * seconds)  # Total chunks to process
    noise_floor = 10.0  # Initial noise floor estimate
    clipping_count = 0  # Count of clipped audio chunks
    signal_sum = 0  # Sum of sound levels for SNR calculation
    noise_sum = 0  # Sum of background noise levels
    freq_analysis = []  # Frequency analysis data storage

    # Process audio data in chunks
    for i in range(0, total_chunks):
        try:
            # Read audio data from stream
            data = np.frombuffer(
                stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16
            )
        except Exception as e:
            print(f"Error reading audio: {e}")
            continue

        # Calculate volume using Root Mean Square (RMS)
        if len(data) > 0:
            rms = np.sqrt(np.mean(np.square(data.astype(np.float32))))
        else:
            rms = 0

        # Frequency analysis using Fast Fourier Transform (FFT)
        if len(data) > 0:
            fft_data = np.fft.fft(data.astype(np.float32))
            freqs = np.fft.fftfreq(len(fft_data), 1.0 / RATE)
            positive_freq_idx = np.where(freqs > 0)  # Only positive frequencies
            fft_spectrum = np.abs(fft_data[positive_freq_idx])
            freq_analysis.append(fft_spectrum)
        else:
            fft_spectrum = np.array([0])
            freq_analysis.append(fft_spectrum)

        # Update ambient noise level using exponential moving average
        if rms < noise_floor * 1.5:  # Only update if not too far from current estimate
            noise_floor = 0.95 * noise_floor + 0.05 * rms

        # Dynamic threshold based on ambient noise
        dynamic_threshold = noise_floor * threshold_multiplier

        # Check for sound detection above threshold
        if rms > dynamic_threshold:  # Sound detected
            sound_count += 1
            signal_sum += rms
        else:  # Background noise
            noise_sum += rms

        # Detect clipping (audio distortion when signal exceeds maximum range)
        if (
            len(data) > 0 and np.max(np.abs(data)) > 32700
        ):  # 32700 is slightly below 16-bit max (32767)
            clipping_count += 1

    # Calculate final metrics
    if total_chunks == 0:
        print("No chunks processed")
        stream.stop_stream()
        stream.close()
        audio.terminate()
        return None

    # Microphone health percentage (activity detection rate)
    mic_health = (sound_count / total_chunks) * 100

    # Calculate average signal and noise with protection against division by zero
    avg_signal = signal_sum / sound_count if sound_count > 0 else 0
    avg_noise = (
        noise_sum / (total_chunks - sound_count)
        if (total_chunks - sound_count) > 0
        else noise_floor
    )

    # Calculate Signal-to-Noise Ratio (SNR) in decibels
    if avg_signal > 0 and avg_noise > 0:
        snr = 10 * np.log10(avg_signal / avg_noise)
    else:
        snr = 0  # Default value when SNR can't be calculated

    # Calculate clipping percentage
    avg_clipping = (clipping_count / total_chunks) * 100

    # Frequency response analysis
    if freq_analysis and len(freq_analysis) > 0:
        try:
            avg_fft_spectrum = np.mean(freq_analysis, axis=0)
            # Calculate how much of the frequency spectrum has significant energy
            threshold = (
                np.percentile(avg_fft_spectrum, 75) if len(avg_fft_spectrum) > 0 else 0
            )
            freq_range_coverage = (
                np.mean(avg_fft_spectrum > threshold) * 100 if threshold > 0 else 0
            )
        except:
            freq_range_coverage = 0
    else:
        freq_range_coverage = 0

    # Clean up audio resources
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Compile comprehensive health report
    health_report = {
        "Microphone Health (%)": mic_health,
        "Average Signal-to-Noise Ratio (dB)": snr,
        "Clipping Percentage (%)": avg_clipping,
        "Frequency Range Coverage (%)": freq_range_coverage,
        "Noise Floor": noise_floor,
    }

    return health_report


def mic_health():
    """
    Main microphone health checking routine with user interaction.

    Guides the user through:
    1. Listing available input devices
    2. Selecting a device to test
    3. Performing health analysis
    4. Reporting results via voice

    Handles user input errors gracefully with fallback to default device.
    """
    # List available devices
    devices = list_input_devices()

    # Ask user which device to test
    try:
        speak("Enter the device number you want to test: ")
        choice = int(input())

        # Validate choice
        valid_choices = [device[0] for device in devices]
        if choice not in valid_choices:
            speak(f"Invalid choice. Using default device.")
            choice = None
    except:
        speak("Invalid input. Using default device.")
        choice = None

    # Perform microphone health analysis
    health_metrics = get_mic_health(seconds=3, device_index=choice)

    # Report results
    if health_metrics:
        for metric, value in health_metrics.items():
            output = f"{metric}: {value:.2f}"
            speak(output)
    else:
        speak(
            "Unable to check microphone health. Please ensure a microphone is connected."
        )


if __name__ == "__main__":
    """
    Entry point for standalone microphone health testing.

    When run directly, this script will:
    1. List available microphones
    2. Allow user selection
    3. Perform comprehensive health analysis
    4. Report results via voice
    """
    mic_health()
