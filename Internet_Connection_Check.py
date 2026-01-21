import sys
import requests

def internet_connection_test(url: str = "https://www.google.com/", timeout: float = 5.0) -> bool:
    """
    Returns True if we can reach the URL within timeout and get a 2xx/3xx response.
    Uses HEAD to minimize data transfer.
    """
    print(f"Attempting to connect to {url} to determine internet connection status.")
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        ok = 200 <= resp.status_code < 400
        if ok:
            print(f"Connection to {url} was successful (status {resp.status_code}).")
        else:
            print(f"Reached {url} but got unexpected status {resp.status_code}.")
        return ok
    except requests.exceptions.Timeout:
        print(f"Failed to connect to {url}: timed out after {timeout}s.")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"Failed to connect to {url}: {e}")
        return False
    except requests.exceptions.RequestException as e:
        # Catches other errors like TooManyRedirects, SSLError, etc.
        print(f"Failed with request error: {e}")
        return False
    except Exception as e:
        print(f"Failed with unparsed reason: {e}")
        return False

if __name__ == "__main__":
    success = internet_connection_test()
    # Exit code is useful if running from scripts/CI
    sys.exit(0 if success else 1)