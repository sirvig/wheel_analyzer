"""
Stock quote fetching from marketdata.app API.
Endpoint: GET /v1/stocks/quotes/{symbol}
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MARKETDATA_BASE_URL = "https://api.marketdata.app"


def get_stock_quote(symbol: str) -> dict[str, Any] | None:
    """
    Fetch current stock quote from marketdata.app.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        dict: Quote data with keys: 'symbol', 'price', 'updated'
        None: If API request fails

    Example response:
        {
            'symbol': 'AAPL',
            'price': Decimal('150.25'),
            'updated': '2025-01-13T21:00:00Z'
        }
    """
    # Validate API key is configured
    if not settings.MD_API_KEY:
        logger.error("MD_API_KEY not configured in settings")
        return None

    url = f"{MARKETDATA_BASE_URL}/v1/stocks/quotes/{symbol}/"

    params = {"token": settings.MD_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # marketdata.app returns arrays for all fields
        # Extract first element from each array
        return {
            "symbol": data["symbol"][0],
            "price": Decimal(str(data["last"][0])),
            "updated": data["updated"][0],  # Unix timestamp (integer)
        }

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching quote for {symbol}")
        return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Symbol not found: {symbol}")
        elif e.response.status_code == 429:
            logger.critical(f"Rate limit exceeded for {symbol}")
        else:
            logger.error(f"HTTP error fetching {symbol}: {e}")
        return None

    except (
        KeyError,
        ValueError,
        InvalidOperation,
        requests.exceptions.RequestException,
    ) as e:
        logger.error(f"Error parsing quote for {symbol}: {e}")
        return None
