"""Module for measuring and reporting internet connection performance via voice."""

from assistant.core.speak_selector import speak
import speedtest
import threading
from assistant.core.registry import on_fuzzy


def check_internet_speed() -> None:
    """
    Performs an internet speed test and announces the results via voice.

    Measures download speed, upload speed, and ping latency using the speedtest-cli
    library, then provides a qualitative assessment of the download performance.
    """
    try:
        speak("Testing your internet speed, this may take a moment...")

        st = speedtest.Speedtest()
        st.timeout = 60

        best_server = st.get_best_server()
        speak(
            f"Testing against server: {best_server['sponsor']} ({best_server['name']})"
        )

        speak("Measuring download speed...")
        download_speed = (
            st.download() / 1_000_000
        )

        speak("Measuring upload speed...")
        upload_speed = st.upload() / 1_000_000

        results = st.results.dict()
        ping_result = results["ping"]

        if download_speed > 70:
            speed_comment = "which is excellent"
        elif download_speed > 40:
            speed_comment = "which is good"
        elif download_speed > 25:
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


@on_fuzzy(["check internet speed", "check the internet speed", "run internet speed test", "check internet connection", "internet speed"], score_cutoff=90)
def handle_speedtest():
    """Triggers the internet speed test in a background thread."""
    threading.Thread(target=check_internet_speed, daemon=True).start()
