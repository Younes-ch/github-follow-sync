from termcolor import cprint

import requests
import sys

def send_get_request(url: str, headers: dict) -> requests.Response:
    """Get the response from the url and return it as a dictionary."""
    if headers is None:
        cprint("You need to provide a token!", "red")
        sys.exit()
    else:
        response = requests.get(url, headers=headers)
    return response

def send_delete_request(url: str, headers: dict):
    """Send a delete request to the url."""
    if headers is None:
        cprint("You need to provide a token!", "red")
        sys.exit()
    else:
        response = requests.delete(url, headers=headers)
    return response