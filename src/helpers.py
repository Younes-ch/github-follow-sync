import requests
import sys

def send_get_request(url: str, headers: dict) -> requests.Response:
    """Send a GET request and return the Response."""
    if not headers or not headers.get("Authorization"):
        print("❌ Missing Authorization header. Set TOKEN in your environment.")
        sys.exit(1)
    response = requests.get(url, headers=headers)
    return response

def send_delete_request(url: str, headers: dict) -> requests.Response:
    """Send a DELETE request to the url and return the Response."""
    if not headers or not headers.get("Authorization"):
        print("❌ Missing Authorization header. Set TOKEN in your environment.")
        sys.exit(1)
    response = requests.delete(url, headers=headers)
    return response


def send_put_request(url: str, headers: dict) -> requests.Response:
    """Send a PUT request to the url and return the Response."""
    if not headers or not headers.get("Authorization"):
        print("❌ Missing Authorization header. Set TOKEN in your environment.")
        sys.exit(1)
    response = requests.put(url, headers=headers)
    return response