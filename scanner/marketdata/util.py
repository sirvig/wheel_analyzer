import os
from datetime import datetime, timedelta

import requests


def calculate_annualized_return(strike_price, bid_price, days_to_expiration):
    if bid_price < 0:
        return 0
    if days_to_expiration == 0:
        days_to_expiration = 1
    premium = bid_price * 100
    invested = strike_price * 100

    annualized = (((premium / invested) / days_to_expiration) * 365) * 100
    return annualized


def calculate_percent_change(strike_price, underlying_price):
    return ((underlying_price - strike_price) / strike_price) * 100


def calculate_roll_price(ask_price, bid_price):
    return bid_price - ask_price


def format_contract_date(date_string):
    date_object = datetime.strptime(date_string, "%Y-%m-%d")
    return date_object.strftime("%y%m%d")


def format_contract_strike(strike_price):
    # Convert to string and remove the decimal point
    strike_str = str(strike_price).replace(".", "")
    # Check if there is a decimal point
    if "." not in strike_str:
        strike_str += "00"
    else:
        # Remove the decimal point
        strike_str = strike_str.replace(".", "")
    # Pad with leading zeros to ensure length is 8
    return strike_str.zfill(8)


def get_headers():
    API_KEY = get_api_key()
    headers = {"Accept": "application/json", "Authorization": f"Bearer {API_KEY}"}
    return headers


def get_api_key():
    API_KEY = os.environ.get("MD_API_KEY")
    return API_KEY


def get_base_url():
    URL_BASE = os.environ.get("MD_URL_BASE")
    return URL_BASE


def get_market_data(url):
    data = {}
    headers = get_headers()
    base_url = get_base_url()
    request_url = f"{base_url}{url}"
    response = requests.get(request_url, headers=headers)

    # Checking if the request was successful
    if response.status_code in (200, 203):
        # Parsing the JSON response
        data = response.json()
    else:
        print(f"Failed to retrieve data for url {request_url}: {response.status_code}")

    return data


def get_fridays(num_of_fridays=5):
    today = datetime.today()
    current_day = today.weekday()
    days_ahead = 4 - current_day
    if current_day >= 4:
        days_ahead += 7

    fridays = []
    for i in range(1, num_of_fridays + 1):
        next_friday = today + timedelta(days=days_ahead + (i - 1) * 7)
        fridays.append(next_friday.strftime("%Y-%m-%d"))

    return fridays


def get_desired_delta(contract_type, days_to_expiration):
    put_delta = -0.20
    call_delta = 0.20

    if days_to_expiration <= 7:
        if contract_type == "put":
            return put_delta
        else:
            return call_delta
    elif days_to_expiration <= 14:
        if contract_type == "put":
            return put_delta - 0.04
        else:
            return call_delta + 0.04
    elif days_to_expiration <= 21:
        if contract_type == "put":
            return put_delta - 0.08
        else:
            return call_delta + 0.08
    elif days_to_expiration <= 28:
        if contract_type == "put":
            return put_delta - 0.12
        else:
            return call_delta + 0.12
    else:
        if contract_type == "put":
            return put_delta - 0.16
        else:
            return call_delta + 0.16


def is_market_open(now=datetime.now()):
    if (
        now.weekday() < 5  # Monday to Friday
        and (now.hour > 9 or (now.hour == 9 and now.minute >= 30))  # After 9:30 AM
        and now.hour < 16  # Before 4:00 PM
    ):
        return True
    return False
