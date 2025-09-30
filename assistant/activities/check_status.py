import requests


def is_online(url="https://www.google.com", timeout=5):
    """
    Check internet connectivity by attempting to reach a specified URL.

    This function tests network connectivity by making an HTTP GET request
    to a target website. It's commonly used to verify if the system has
    active internet access before attempting network-dependent operations.

    Args:
        url (str): The URL to test connectivity against. Defaults to Google
                   as it's highly reliable and globally accessible.
        timeout (int): Maximum time in seconds to wait for server response.
                      Prevents hanging on slow or unresponsive connections.

    Returns:
        bool: True if the request succeeds with HTTP status code 200-299,
              False if connection fails or times out.

    Examples:
        >>> is_online()
        True  # If internet connection is available
        >>> is_online("https://www.github.com")
        True  # If GitHub is accessible
        >>> is_online(timeout=2)
        False  # If connection times out in 2 seconds

    Note:
        The function specifically catches ConnectionError exceptions but
        allows other exceptions to propagate, as they may indicate more
        serious issues that should be handled by the caller.
    """
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code >= 200 and response.status_code < 300
    except requests.ConnectionError:
        return False
