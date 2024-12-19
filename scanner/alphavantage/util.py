import os

import requests


def get_api_key():
    API_KEY = os.environ.get("AV_API_KEY")
    return API_KEY


def get_base_url():
    URL_BASE = os.environ.get("AV_URL_BASE")
    return URL_BASE


def get_market_data(url):
    data = {}
    base_url = get_base_url()
    request_url = f"{base_url}{url}&apikey={get_api_key()}"
    response = requests.get(request_url)

    # Checking if the request was successful
    if response.status_code in (200, 203):
        # Parsing the JSON response
        data = response.json()
    else:
        print(f"Failed to retrieve data for url {request_url}: {response.status_code}")

    return data
