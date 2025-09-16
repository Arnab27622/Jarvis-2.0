from assistant.core.speak_selector import speak
import speedtest


def check_internet_speed():
    """Check and speak internet download and upload speeds"""

    try:
        speak("Testing your internet speed, this may take a moment...")

        # Create speedtest object with timeout
        st = speedtest.Speedtest()
        st.timeout = 60  # Set timeout to 60 seconds

        # Get the best server
        best_server = st.get_best_server()
        speak(
            f"Testing against server: {best_server['sponsor']} ({best_server['name']})"
        )

        # Test download speed
        speak("Measuring download speed...")
        download_speed = st.download() / 1_000_000  # Convert to Mbps

        # Test upload speed
        speak("Measuring upload speed...")
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps

        # Get ping and other details
        results = st.results.dict()
        ping_result = results["ping"]

        # Format results
        if download_speed > 50:
            speed_comment = "which is excellent"
        elif download_speed > 25:
            speed_comment = "which is good"
        elif download_speed > 10:
            speed_comment = "which is average"
        else:
            speed_comment = "which is below average"

        result_message = (
            f"Your internet speed test results: "
            f"Download: {download_speed:.2f} Mbps {speed_comment}, "
            f"Upload: {upload_speed:.2f} Mbps, "
            f"and Ping: {ping_result:.2f} milliseconds. "
        )

        speak(result_message)

    except speedtest.SpeedtestBestServerFailure:
        speak(
            "Could not find a suitable server for testing. Please check your internet connection."
        )
    except speedtest.SpeedtestException as e:
        error_msg = f"Speed test error: {str(e)}"
        print(error_msg)
        speak(
            "Sorry, the speed test failed. Please ensure you're connected to the internet."
        )
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        speak("An unexpected error occurred during the speed test.")
