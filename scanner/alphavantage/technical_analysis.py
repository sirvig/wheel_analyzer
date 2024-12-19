import logging

logger = logging.getLogger(__name__)
DEBUG = False


def find_sma(ticker, period, interval="daily"):
    """
    Find the simple moving average for a stock
    """
    from scanner.alphavantage.util import get_market_data

    url = f"?function=SMA&symbol={ticker}&interval={interval}&time_period={period}&series_type=open"
    data = get_market_data(url)

    return data
