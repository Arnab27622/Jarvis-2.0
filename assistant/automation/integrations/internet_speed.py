from assistant.core.speak_selector import speak
import speedtest


def check_internet_speed():
    """
    Perform comprehensive internet speed test and report results via voice.

    This function uses the speedtest-cli library to measure internet connection
    performance across three key metrics: download speed, upload speed, and ping
    latency. It provides both quantitative results and qualitative assessment.

    Test Metrics:
        - Download Speed: How fast data can be received (in Mbps)
        - Upload Speed: How fast data can be sent (in Mbps)
        - Ping Latency: Response time between client and server (in milliseconds)

    Speed Classification:
        - Excellent: > 50 Mbps download
        - Good: 25-50 Mbps download
        - Average: 10-25 Mbps download
        - Below Average: < 10 Mbps download

    Process:
        1. Finds optimal test server based on geographic proximity
        2. Measures download speed with progress feedback
        3. Measures upload speed with progress feedback
        4. Compiles results with qualitative assessment
        5. Reports comprehensive results via voice

    Example Output:
        "Your internet speed test results: Download: 45.67 Mbps which is good,
         Upload: 12.34 Mbps, and Ping: 24.56 milliseconds."

    Raises:
        SpeedtestBestServerFailure: When no suitable test servers can be found
        SpeedtestException: For general speed test failures
        Exception: For unexpected errors during testing

    Note:
        The test may take 30-60 seconds to complete as it transfers actual data
        to accurately measure connection speeds. A stable internet connection
        is required for accurate results.
    """
    try:
        speak("Testing your internet speed, this may take a moment...")

        # Create speedtest object with timeout to prevent hanging
        st = speedtest.Speedtest()
        st.timeout = 60  # Set timeout to 60 seconds

        # Find and connect to the optimal test server based on latency and capacity
        best_server = st.get_best_server()
        speak(
            f"Testing against server: {best_server['sponsor']} ({best_server['name']})"
        )

        # Test download speed (data receiving capability)
        speak("Measuring download speed...")
        download_speed = (
            st.download() / 1_000_000
        )  # Convert from bits per second to Mbps

        # Test upload speed (data sending capability)
        speak("Measuring upload speed...")
        upload_speed = st.upload() / 1_000_000  # Convert from bits per second to Mbps

        # Get ping latency (server response time)
        results = st.results.dict()
        ping_result = results["ping"]

        # Classify download speed for user-friendly assessment
        if download_speed > 60:
            speed_comment = "which is excellent"
        elif download_speed > 40:
            speed_comment = "which is good"
        elif download_speed > 25:
            speed_comment = "which is average"
        else:
            speed_comment = "which is below average"

        # Compile comprehensive results report
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
