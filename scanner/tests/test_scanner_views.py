"""Tests for scanner views."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestIndexView:
    """Tests for the scanner index view."""

    def test_index_view_renders_successfully(self, client):
        """Test that the index view renders without errors."""
        with patch("scanner.views.r") as mock_redis:
            # Mock Redis responses
            mock_redis.keys.return_value = []
            mock_redis.get.return_value = b"2024-11-03 10:00"

            response = client.get(reverse("scanner_index"))

            assert response.status_code == 200
            assert "last_scan" in response.context
            assert response.context["last_scan"] == "2024-11-03 10:00"

    def test_index_view_displays_options_data(self, client):
        """Test that the index view displays options data from Redis."""
        with patch("scanner.views.r") as mock_redis:
            # Mock Redis responses with sample data
            mock_redis.keys.return_value = [b"put_AAPL", b"put_MSFT"]

            # Mock options data
            aapl_options = [
                {
                    "date": "2024-12-20",
                    "strike": 180.0,
                    "price": 2.50,
                    "delta": -0.15,
                    "annualized": 35.5,
                }
            ]
            msft_options = [
                {
                    "date": "2024-12-20",
                    "strike": 400.0,
                    "price": 3.00,
                    "delta": -0.18,
                    "annualized": 32.0,
                }
            ]

            def mock_hget(key, field):
                if key == b"put_AAPL":
                    if field == "options":
                        return json.dumps(aapl_options).encode()
                    elif field == "last_scan":
                        return b"2024-11-03 10:00"
                elif key == b"put_MSFT":
                    if field == "options":
                        return json.dumps(msft_options).encode()
                    elif field == "last_scan":
                        return b"2024-11-03 10:05"
                return None

            mock_redis.hget.side_effect = mock_hget
            mock_redis.get.return_value = b"2024-11-03 10:05"

            response = client.get(reverse("scanner_index"))

            assert response.status_code == 200
            assert "ticker_options" in response.context
            assert "AAPL" in response.context["ticker_options"]
            assert "MSFT" in response.context["ticker_options"]
            assert len(response.context["ticker_options"]["AAPL"]) == 1
            assert len(response.context["ticker_options"]["MSFT"]) == 1

    def test_index_view_handles_no_options(self, client):
        """Test that the index view handles case with no options found."""
        with patch("scanner.views.r") as mock_redis:
            # Mock Redis responses with empty options
            mock_redis.keys.return_value = [b"put_AAPL"]

            def mock_hget(key, field):
                if key == b"put_AAPL" and field == "options":
                    return json.dumps([]).encode()
                return None

            mock_redis.hget.side_effect = mock_hget
            mock_redis.get.return_value = b"2024-11-03 10:00"

            response = client.get(reverse("scanner_index"))

            assert response.status_code == 200
            assert "ticker_options" in response.context
            assert "AAPL" not in response.context["ticker_options"]


@pytest.mark.django_db
class TestScanView:
    """Tests for the manual scan view."""

    def test_scan_view_requires_post(self, client):
        """Test that scan view only accepts POST requests."""
        response = client.get(reverse("scan"))
        assert response.status_code == 405  # Method Not Allowed

    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_prevents_concurrent_scans(
        self, mock_redis, mock_perform_scan, client
    ):
        """Test that scan view prevents concurrent scans using Redis lock."""
        # Simulate existing lock
        mock_redis.exists.return_value = True

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        assert b"scan is already in progress" in response.content
        # perform_scan should not be called
        mock_perform_scan.assert_not_called()

    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_successful_scan(self, mock_redis, mock_perform_scan, client):
        """Test successful scan execution."""
        # Mock Redis lock (no existing lock)
        mock_redis.exists.return_value = False
        mock_redis.keys.return_value = [b"put_AAPL"]

        # Mock successful scan result
        mock_perform_scan.return_value = {
            "success": True,
            "message": "Scan completed successfully",
            "scanned_count": 26,
            "timestamp": "2024-11-03 10:30",
        }

        # Mock options data for response
        aapl_options = [
            {
                "date": "2024-12-20",
                "strike": 180.0,
                "price": 2.50,
                "delta": -0.15,
                "annualized": 35.5,
            }
        ]

        def mock_hget(key, field):
            if key == b"put_AAPL":
                if field == "options":
                    return json.dumps(aapl_options).encode()
                elif field == "last_scan":
                    return b"2024-11-03 10:30"
            return None

        mock_redis.hget.side_effect = mock_hget

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        # Verify perform_scan was called
        mock_perform_scan.assert_called_once_with(debug=False)
        # Verify lock was set and released
        mock_redis.setex.assert_called_once_with("scan_in_progress", 600, "1")
        mock_redis.delete.assert_called_once_with("scan_in_progress")

    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_handles_market_closed(
        self, mock_redis, mock_perform_scan, client
    ):
        """Test scan view handles market closed scenario."""
        # Mock Redis lock (no existing lock)
        mock_redis.exists.return_value = False

        # Mock market closed result
        mock_perform_scan.return_value = {
            "success": False,
            "message": "Market is closed. Scans only run during market hours (9:30 AM - 4:00 PM ET).",
            "scanned_count": 0,
            "timestamp": "2024-11-03 20:00",
        }

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        assert b"Market is closed" in response.content
        # Verify lock was still released
        mock_redis.delete.assert_called_once_with("scan_in_progress")

    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_handles_errors(self, mock_redis, mock_perform_scan, client):
        """Test scan view handles errors gracefully."""
        # Mock Redis lock (no existing lock)
        mock_redis.exists.return_value = False

        # Mock error result
        mock_perform_scan.return_value = {
            "success": False,
            "message": "An error occurred during the scan. Please check logs for details.",
            "scanned_count": 0,
            "timestamp": "2024-11-03 10:30",
            "error": "Connection timeout",
        }

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        assert b"An error occurred" in response.content
        # Verify lock was released
        mock_redis.delete.assert_called_once_with("scan_in_progress")

    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_releases_lock_on_exception(
        self, mock_redis, mock_perform_scan, client
    ):
        """Test that scan view releases lock even when exception occurs."""
        # Mock Redis lock (no existing lock)
        mock_redis.exists.return_value = False

        # Mock exception during scan
        mock_perform_scan.side_effect = Exception("Unexpected error")

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        assert b"An error occurred" in response.content
        # Verify lock was still released in finally block
        mock_redis.delete.assert_called_once_with("scan_in_progress")

    @patch("scanner.views.settings")
    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_bypasses_market_hours_in_local_environment(
        self, mock_redis, mock_perform_scan, mock_settings, client
    ):
        """Test that scan view bypasses market hours check in LOCAL environment."""
        # Mock Redis lock (no existing lock)
        mock_redis.exists.return_value = False
        mock_redis.keys.return_value = []

        # Set ENVIRONMENT to LOCAL
        mock_settings.ENVIRONMENT = "LOCAL"

        # Mock successful scan result
        mock_perform_scan.return_value = {
            "success": True,
            "message": "Scan completed successfully",
            "scanned_count": 5,
            "timestamp": "2024-11-03 22:00",  # Outside market hours
        }

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        # Verify perform_scan was called with debug=True in LOCAL environment
        mock_perform_scan.assert_called_once_with(debug=True)

    @patch("scanner.views.settings")
    @patch("scanner.views.perform_scan")
    @patch("scanner.views.r")
    def test_scan_view_enforces_market_hours_in_production_environment(
        self, mock_redis, mock_perform_scan, mock_settings, client
    ):
        """Test that scan view enforces market hours check in PRODUCTION environment."""
        # Mock Redis lock (no existing lock)
        mock_redis.exists.return_value = False
        mock_redis.keys.return_value = []

        # Set ENVIRONMENT to PRODUCTION
        mock_settings.ENVIRONMENT = "PRODUCTION"

        # Mock market closed result
        mock_perform_scan.return_value = {
            "success": False,
            "message": "Market is closed. Scans only run during market hours (9:30 AM - 4:00 PM ET).",
            "scanned_count": 0,
            "timestamp": "2024-11-03 22:00",
        }

        response = client.post(reverse("scan"))

        assert response.status_code == 200
        # Verify perform_scan was called with debug=False in PRODUCTION environment
        mock_perform_scan.assert_called_once_with(debug=False)


@pytest.mark.django_db
class TestOptionsListView:
    """Tests for the options list view."""

    def test_options_list_view_renders_for_ticker(self, client):
        """Test that options list view renders for a specific ticker."""
        with patch("scanner.views.r") as mock_redis:
            # Mock Redis responses
            aapl_options = [
                {
                    "date": "2024-12-20",
                    "strike": 180.0,
                    "price": 2.50,
                    "delta": -0.15,
                    "annualized": 35.5,
                }
            ]

            def mock_hget(key, field):
                if key == "put_AAPL" and field == "options":
                    return json.dumps(aapl_options).encode()
                return None

            mock_redis.hget.side_effect = mock_hget

            response = client.get(reverse("options_list", kwargs={"ticker": "AAPL"}))

            assert response.status_code == 200
            assert "ticker" in response.context
            assert response.context["ticker"] == "AAPL"
            assert "options" in response.context
            assert len(response.context["options"]) == 1
            assert response.context["options"][0]["strike"] == 180.0


# Valuation List View Tests
class TestValuationListView:
    """Tests for the valuation list view."""

    @pytest.mark.django_db
    def test_valuation_list_requires_authentication(self, client):
        """Valuation list view requires user to be logged in."""
        response = client.get("/scanner/valuations/")

        # Should redirect to login
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    @pytest.mark.django_db
    def test_valuation_list_authenticated(self, client, user):
        """Authenticated user can access valuation list."""
        client.force_login(user)

        response = client.get("/scanner/valuations/")

        # Should succeed
        assert response.status_code == 200
        assert "scanner/valuations.html" in [t.name for t in response.templates]

    @pytest.mark.django_db
    def test_valuation_list_shows_active_stocks_only(self, client, user):
        """Valuation list shows only active curated stocks."""
        from scanner.factories import CuratedStockFactory

        # Create active and inactive stocks
        active1 = CuratedStockFactory(symbol="ATEST1", active=True)
        active2 = CuratedStockFactory(symbol="ATEST2", active=True)
        inactive = CuratedStockFactory(symbol="ITEST", active=False)

        client.force_login(user)
        response = client.get("/scanner/valuations/")

        stocks = response.context["stocks"]

        # Should include active stocks
        assert active1 in stocks
        assert active2 in stocks

        # Should NOT include inactive stock
        assert inactive not in stocks

    @pytest.mark.django_db
    def test_valuation_list_ordered_by_symbol(self, client, user):
        """Valuation list is ordered alphabetically by symbol."""
        from scanner.factories import CuratedStockFactory

        # Create stocks in non-alphabetical order
        CuratedStockFactory(symbol="ZTEST", active=True)
        CuratedStockFactory(symbol="BTEST", active=True)
        CuratedStockFactory(symbol="MTEST", active=True)

        client.force_login(user)
        response = client.get("/scanner/valuations/")

        stocks = response.context["stocks"]
        symbols = [stock.symbol for stock in stocks]

        # Should be in alphabetical order
        assert symbols == sorted(symbols)

    @pytest.mark.django_db
    def test_valuation_list_context_includes_stocks(self, client, user):
        """Valuation list context includes stocks queryset."""
        from scanner.factories import CuratedStockFactory

        stock = CuratedStockFactory(symbol="CTEST", active=True)

        client.force_login(user)
        response = client.get("/scanner/valuations/")

        # Should have stocks in context
        assert "stocks" in response.context

        stocks = response.context["stocks"]
        assert stocks.count() > 0
        assert stock in stocks

    @pytest.mark.django_db
    def test_valuation_list_handles_no_stocks(self, client, user):
        """Valuation list handles case with no active stocks."""
        from scanner.models import CuratedStock

        # Deactivate all stocks
        CuratedStock.objects.update(active=False)

        client.force_login(user)
        response = client.get("/scanner/valuations/")

        # Should still succeed with empty queryset
        assert response.status_code == 200
        assert response.context["stocks"].count() == 0

    @pytest.mark.django_db
    def test_valuation_list_displays_intrinsic_values(self, client, user):
        """Valuation list can display stocks with NULL intrinsic values."""
        from decimal import Decimal
        from scanner.factories import CuratedStockFactory

        # Stock with values
        stock_with_values = CuratedStockFactory(
            symbol="VTEST1",
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("148.00"),
            active=True,
        )

        # Stock with NULL values
        stock_without_values = CuratedStockFactory(
            symbol="VTEST2",
            intrinsic_value=None,
            intrinsic_value_fcf=None,
            active=True,
        )

        client.force_login(user)
        response = client.get("/scanner/valuations/")

        # Should succeed without errors
        assert response.status_code == 200

        stocks = response.context["stocks"]
        assert stock_with_values in stocks
        assert stock_without_values in stocks
