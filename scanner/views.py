import json
import os

import redis
from django.shortcuts import render

r = redis.Redis.from_url(os.environ.get("REDIS_URL"))


def index(request):
    keys = r.keys("put_*")

    context = {}
    tickers = []
    for key in keys:
        ticker = key.decode("utf-8").split("_")[1]
        options = json.loads(r.get(key).decode("utf-8"))
        if len(options) > 0:
            tickers.append(ticker)

    context["tickers"] = tickers
    context["last_scan"] = r.get("last_run").decode("utf-8")

    # TEMP WORK
    ticker_options = {}
    for key in keys:
        ticker = key.decode("utf-8").split("_")[1]
        options = json.loads(r.get(key).decode("utf-8"))
        if len(options) > 0:
            ticker_options[ticker] = options

    sorted_ticker_options = {k: ticker_options[k] for k in sorted(ticker_options)}
    context["ticker_options"] = sorted_ticker_options
    # END TEMP WORK

    return render(request, "scanner/options_list.html", context)


def options_list(request, ticker):
    key = f"put_{ticker}"
    options = json.loads(r.get(key).decode("utf-8"))

    context = {"ticker": ticker, "options": options}

    # ticker_options = {}
    # for key in keys:
    #     ticker = key.decode("utf-8").split("_")[1]
    #     options = json.loads(r.get(key).decode("utf-8"))
    #     if len(options) > 0:
    #         ticker_options[ticker] = options

    # context["ticker_options"] = ticker_options
    return render(request, "scanner/options_list.html", context)
