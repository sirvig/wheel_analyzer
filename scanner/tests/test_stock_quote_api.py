"""
Tests for Phase 8: Stock Price Integration - Marketdata API Client.

This module tests the get_stock_quote() function from scanner/marketdata/quotes.py
covering successful fetches, timeouts, HTTP errors, and network failures.
"""

import requests
from decimal import Decimal
from unittest.mock import patch, Mock

from scanner.marketdata.quotes import get_stock_quote


# ===== Successful API Response Tests =====

class TestGetStockQuoteSuccess:
    """Tests for successful stock quote API calls."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_successful_fetch(self, mock_get):
        """Test successful quote fetch with valid data."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['AAPL'],
            'last': [150.25],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('AAPL')

        # Assert
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert result['price'] == Decimal('150.25')
        assert result['updated'] == 1763144253  # Unix timestamp
        mock_get.assert_called_once()

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_decimal_conversion(self, mock_get):
        """Test that price is correctly converted to Decimal."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['MSFT'],
            'last': [420.75],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('MSFT')

        # Assert
        assert isinstance(result['price'], Decimal)
        assert result['price'] == Decimal('420.75')

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_calls_api_with_correct_params(self, mock_get):
        """Test that API is called with correct URL and parameters."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['GOOGL'],
            'last': [140.50],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        get_stock_quote('GOOGL')

        # Assert
        call_args = mock_get.call_args
        assert 'GOOGL' in call_args[0][0]  # URL contains symbol
        assert call_args[1]['timeout'] == 30  # 30 second timeout
        assert 'token' in call_args[1]['params']  # API key in params

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_handles_float_precision(self, mock_get):
        """Test handling of float precision in API response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['AMZN'],
            'last': [175.123456789],  # High precision float
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('AMZN')

        # Assert
        assert result['price'] == Decimal('175.123456789')


# ===== Timeout Error Tests =====

class TestGetStockQuoteTimeout:
    """Tests for timeout scenarios."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_timeout_error(self, mock_get):
        """Test that timeout exception is handled gracefully."""
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        # Act
        result = get_stock_quote('AAPL')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_timeout_logs_error(self, mock_logger, mock_get):
        """Test that timeout is logged at ERROR level."""
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        # Act
        get_stock_quote('MSFT')

        # Assert
        mock_logger.error.assert_called_once()
        assert 'Timeout' in str(mock_logger.error.call_args)
        assert 'MSFT' in str(mock_logger.error.call_args)


# ===== HTTP Error Tests =====

class TestGetStockQuoteHTTPErrors:
    """Tests for HTTP error responses."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_404_not_found(self, mock_get):
        """Test handling of 404 Not Found (invalid symbol)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('INVALID')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_404_logs_warning(self, mock_logger, mock_get):
        """Test that 404 is logged as WARNING (not critical)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Act
        get_stock_quote('NOTFOUND')

        # Assert
        mock_logger.warning.assert_called_once()
        assert 'not found' in str(mock_logger.warning.call_args).lower()

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_429_rate_limit(self, mock_get):
        """Test handling of 429 Too Many Requests (rate limit)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('AAPL')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_429_logs_critical(self, mock_logger, mock_get):
        """Test that rate limit is logged as CRITICAL (requires attention)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Act
        get_stock_quote('MSFT')

        # Assert
        mock_logger.critical.assert_called_once()
        assert 'Rate limit' in str(mock_logger.critical.call_args)

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_500_server_error(self, mock_get):
        """Test handling of 500 Internal Server Error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('GOOGL')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_500_logs_error(self, mock_logger, mock_get):
        """Test that 500 error is logged at ERROR level."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Act
        get_stock_quote('AMZN')

        # Assert
        mock_logger.error.assert_called_once()
        assert 'HTTP error' in str(mock_logger.error.call_args)


# ===== Network Error Tests =====

class TestGetStockQuoteNetworkErrors:
    """Tests for network-related errors."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_connection_error(self, mock_get):
        """Test handling of connection errors."""
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        # Act
        result = get_stock_quote('TSLA')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_connection_error_logs(self, mock_logger, mock_get):
        """Test that connection error is logged."""
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        # Act
        get_stock_quote('NVDA')

        # Assert
        mock_logger.error.assert_called_once()

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_request_exception(self, mock_get):
        """Test handling of generic RequestException."""
        # Arrange
        mock_get.side_effect = requests.exceptions.RequestException("Unknown error")

        # Act
        result = get_stock_quote('META')

        # Assert
        assert result is None


# ===== Data Parsing Error Tests =====

class TestGetStockQuoteParsingErrors:
    """Tests for JSON parsing and data extraction errors."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_missing_symbol_field(self, mock_get):
        """Test handling of missing 'symbol' field in response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'last': [150.00],
            'updated': [1763144253]
            # 'symbol' field missing
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('AAPL')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_missing_price_field(self, mock_get):
        """Test handling of missing 'last' price field in response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['MSFT'],
            'updated': [1763144253]
            # 'last' field missing
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('MSFT')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_invalid_price_value(self, mock_get):
        """Test handling of non-numeric price value."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['GOOGL'],
            'last': ['invalid_price'],  # String instead of number
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('GOOGL')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_parsing_error_logs(self, mock_logger, mock_get):
        """Test that parsing errors are logged."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['AMZN'],
            'last': ['bad_data'],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        get_stock_quote('AMZN')

        # Assert
        mock_logger.error.assert_called_once()
        assert 'parsing' in str(mock_logger.error.call_args).lower()

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_empty_json_response(self, mock_get):
        """Test handling of empty JSON response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('TSLA')

        # Assert
        assert result is None

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_null_price_value(self, mock_get):
        """Test handling of null price value."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['NVDA'],
            'last': [None],  # Null price
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('NVDA')

        # Assert
        assert result is None


# ===== Edge Case Tests =====

class TestGetStockQuoteEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_zero_price(self, mock_get):
        """Test handling of zero price (valid but unusual)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['ZERO'],
            'last': [0.0],  # Zero price
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('ZERO')

        # Assert
        assert result is not None
        assert result['price'] == Decimal('0.0')

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_very_high_price(self, mock_get):
        """Test handling of very high stock price."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['BRK.A'],
            'last': [540000.00],  # Berkshire Hathaway A shares
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('BRK.A')

        # Assert
        assert result is not None
        assert result['price'] == Decimal('540000.00')

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_very_low_price(self, mock_get):
        """Test handling of very low stock price (penny stock)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['PENNY'],
            'last': [0.0001],  # Penny stock
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('PENNY')

        # Assert
        assert result is not None
        assert result['price'] == Decimal('0.0001')

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_lowercase_symbol(self, mock_get):
        """Test that lowercase symbol is handled correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['aapl'],  # Lowercase in response
            'last': [150.00],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('aapl')

        # Assert
        assert result is not None
        assert result['symbol'] == 'aapl'

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_symbol_with_dot(self, mock_get):
        """Test handling of symbol with dot (e.g., BRK.B)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['BRK.B'],
            'last': [350.00],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('BRK.B')

        # Assert
        assert result is not None
        assert result['symbol'] == 'BRK.B'


# ===== Integration Tests =====

class TestGetStockQuoteIntegration:
    """Integration tests verifying complete API interaction workflow."""

    @patch('scanner.marketdata.quotes.requests.get')
    def test_get_stock_quote_full_success_workflow(self, mock_get):
        """Test complete successful workflow from request to response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': ['AAPL'],
            'last': [175.50],
            'updated': [1763144253]
        }
        mock_get.return_value = mock_response

        # Act
        result = get_stock_quote('AAPL')

        # Assert
        # Verify complete return structure
        assert result is not None
        assert len(result) == 3
        assert 'symbol' in result
        assert 'price' in result
        assert 'updated' in result

        # Verify data types
        assert isinstance(result['symbol'], str)
        assert isinstance(result['price'], Decimal)
        assert isinstance(result['updated'], int)

        # Verify values
        assert result['symbol'] == 'AAPL'
        assert result['price'] == Decimal('175.50')
        assert result['updated'] == 1763144253  # Unix timestamp

    @patch('scanner.marketdata.quotes.requests.get')
    @patch('scanner.marketdata.quotes.logger')
    def test_get_stock_quote_full_failure_workflow(self, mock_logger, mock_get):
        """Test complete failure workflow with proper error handling."""
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        # Act
        result = get_stock_quote('FAIL')

        # Assert
        # Verify None returned
        assert result is None

        # Verify error logged
        mock_logger.error.assert_called_once()

        # Verify exception was handled (no re-raise)
        # Test passes if no exception raised
