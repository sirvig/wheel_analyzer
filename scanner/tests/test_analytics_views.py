"""
Tests for analytics views.

Test coverage:
- analytics_view(): portfolio analytics dashboard rendering
- stock_history_view(): enhanced with quick stats and dual-line chart
- valuation_comparison_view(): enhanced with grouped bar chart
- Chart data JSON serialization and validation
- Authentication requirements
- Empty state handling
- Chart color generation
"""

import pytest
import json
from decimal import Decimal
from datetime import date
from django.urls import reverse
from django.contrib.auth import get_user_model

from scanner.models import CuratedStock, ValuationHistory

User = get_user_model()


@pytest.fixture
def authenticated_user(client):
    """Create and authenticate a test user."""
    user = User.objects.create_user(username='testuser', password='testpass123')
    client.login(username='testuser', password='testpass123')
    return user


@pytest.mark.django_db
class TestAnalyticsView:
    """Tests for analytics_view() function."""

    def test_analytics_view_requires_authentication(self, client):
        """Test analytics view requires login."""
        url = reverse('scanner:analytics')
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_analytics_view_renders_with_data(self, client, authenticated_user):
        """Test analytics view renders with portfolio data."""
        # Create stocks with history
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:analytics')
        response = client.get(url)

        assert response.status_code == 200
        assert 'analytics' in response.context
        assert 'chart_data_json' in response.context
        assert response.context['analytics']['total_stocks'] == 1

    def test_analytics_view_with_no_data(self, client, authenticated_user):
        """Test analytics view with no stocks."""
        url = reverse('scanner:analytics')
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['analytics']['total_stocks'] == 0
        assert response.context['analytics']['stocks_with_history'] == 0

    def test_analytics_view_chart_data_json_format(self, client, authenticated_user):
        """Test analytics view chart data is valid JSON."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:analytics')
        response = client.get(url)

        # Should be valid JSON
        chart_data = json.loads(response.context['chart_data_json'])
        assert 'labels' in chart_data
        assert 'datasets' in chart_data
        assert isinstance(chart_data['datasets'], list)

    def test_analytics_view_with_multiple_stocks(self, client, authenticated_user):
        """Test analytics view with multiple stocks."""
        for symbol in ["TEST1", "TEST2", "TEST3"]:
            stock = CuratedStock.objects.create(
                symbol=symbol,
                active=True,
                preferred_valuation_method="EPS",
            )

            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2025, 1, 1),
                intrinsic_value=Decimal("100.00"),
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        url = reverse('scanner:analytics')
        response = client.get(url)

        assert response.status_code == 200
        portfolio = response.context['analytics']
        assert portfolio['total_stocks'] == 3
        assert len(portfolio['stock_analytics']) == 3

        # Chart should have 3 datasets
        chart_data = json.loads(response.context['chart_data_json'])
        assert len(chart_data['datasets']) == 3


@pytest.mark.django_db
class TestStockHistoryViewEnhancements:
    """Tests for enhanced stock_history_view() with analytics."""

    def test_stock_history_view_includes_chart_data(self, client, authenticated_user):
        """Test stock history view includes chart data."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        assert response.status_code == 200
        assert 'chart_data_json' in response.context

        # Validate JSON structure
        chart_data = json.loads(response.context['chart_data_json'])
        assert 'labels' in chart_data
        assert 'datasets' in chart_data
        # Should have 2 datasets: EPS and FCF
        assert len(chart_data['datasets']) == 2

    def test_stock_history_view_includes_analytics(self, client, authenticated_user):
        """Test stock history view includes analytics data."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        # Create multiple snapshots for analytics
        for snapshot_date, iv in [
            (date(2024, 7, 1), "140.00"),
            (date(2024, 10, 1), "145.00"),
            (date(2025, 1, 1), "150.00"),
        ]:
            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=snapshot_date,
                intrinsic_value=Decimal(iv),
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        assert response.status_code == 200
        assert 'analytics' in response.context
        analytics = response.context['analytics']
        assert analytics['symbol'] == "TEST1"
        assert analytics['data_points'] == 3

    def test_stock_history_view_includes_quick_stats(self, client, authenticated_user):
        """Test stock history view includes quick stats."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        # Create snapshots with varying values
        for snapshot_date, iv in [
            (date(2024, 7, 1), "140.00"),
            (date(2024, 10, 1), "160.00"),
            (date(2025, 1, 1), "150.00"),
        ]:
            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=snapshot_date,
                intrinsic_value=Decimal(iv),
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        assert response.status_code == 200
        assert 'quick_stats' in response.context

        quick_stats = response.context['quick_stats']
        assert 'highest_iv' in quick_stats
        assert 'lowest_iv' in quick_stats
        assert 'average_iv' in quick_stats

        assert quick_stats['highest_iv'] == Decimal("160.00")
        assert quick_stats['lowest_iv'] == Decimal("140.00")


@pytest.mark.django_db
class TestValuationComparisonViewEnhancements:
    """Tests for enhanced valuation_comparison_view() with bar chart."""

    def test_comparison_view_includes_chart_data(self, client, authenticated_user):
        """Test comparison view includes chart data."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="EPS",
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        assert response.status_code == 200
        assert 'chart_data_json' in response.context

        # Validate JSON structure
        chart_data = json.loads(response.context['chart_data_json'])
        assert 'labels' in chart_data
        assert 'datasets' in chart_data
        # Should have 2 datasets: EPS and FCF
        assert len(chart_data['datasets']) == 2

    def test_comparison_view_chart_includes_all_stocks(self, client, authenticated_user):
        """Test comparison view chart includes all active stocks."""
        for symbol in ["TEST1", "TEST2", "TEST3"]:
            CuratedStock.objects.create(
                symbol=symbol,
                active=True,
                intrinsic_value=Decimal("100.00"),
                intrinsic_value_fcf=Decimal("95.00"),
                preferred_valuation_method="EPS",
            )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        chart_data = json.loads(response.context['chart_data_json'])
        # Should have 3 labels (one per stock)
        assert len(chart_data['labels']) == 3
        assert "TEST1" in chart_data['labels']
        assert "TEST2" in chart_data['labels']
        assert "TEST3" in chart_data['labels']

    def test_comparison_view_chart_data_format(self, client, authenticated_user):
        """Test comparison view chart data has correct format."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="EPS",
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        chart_data = json.loads(response.context['chart_data_json'])

        # Check dataset structure
        for dataset in chart_data['datasets']:
            assert 'label' in dataset
            assert 'data' in dataset
            assert 'backgroundColor' in dataset
            assert isinstance(dataset['data'], list)


@pytest.mark.django_db
class TestChartDataValidation:
    """Tests for chart data validation and edge cases."""

    def test_chart_data_with_none_values(self, client, authenticated_user):
        """Test chart handles None intrinsic values."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=None,  # None value
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="FCF",
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=None,  # None value
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="FCF",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Stock history view
        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)
        assert response.status_code == 200

        # Chart data should handle None gracefully
        chart_data = json.loads(response.context['chart_data_json'])
        assert chart_data is not None

    def test_chart_data_json_serialization(self, client, authenticated_user):
        """Test that Decimal values are properly serialized to JSON."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.50"),
            intrinsic_value_fcf=Decimal("145.25"),
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.50"),
            intrinsic_value_fcf=Decimal("145.25"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        # JSON should parse without errors
        chart_data = json.loads(response.context['chart_data_json'])
        assert chart_data is not None

        # Values should be numeric (not strings)
        for dataset in chart_data['datasets']:
            for value in dataset['data']:
                if value is not None:
                    assert isinstance(value, (int, float))

    def test_analytics_view_handles_stocks_without_history(self, client, authenticated_user):
        """Test analytics view gracefully handles stocks without history."""
        # Create stock without history
        CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        # Create stock with history
        stock2 = CuratedStock.objects.create(
            symbol="TEST2",
            active=True,
            preferred_valuation_method="FCF",
        )

        ValuationHistory.objects.create(
            stock=stock2,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="FCF",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:analytics')
        response = client.get(url)

        assert response.status_code == 200
        portfolio = response.context['analytics']
        assert portfolio['total_stocks'] == 2
        assert portfolio['stocks_with_history'] == 1

    def test_chart_color_generation_consistency(self, client, authenticated_user):
        """Test that chart colors are consistently generated."""
        # Create many stocks to test color wrapping
        for i in range(25):  # More than 20 colors available
            stock = CuratedStock.objects.create(
                symbol=f"TEST{i}",
                active=True,
                preferred_valuation_method="EPS",
            )

            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2025, 1, 1),
                intrinsic_value=Decimal("100.00"),
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        url = reverse('scanner:analytics')
        response = client.get(url)

        assert response.status_code == 200
        chart_data = json.loads(response.context['chart_data_json'])

        # All datasets should have colors
        for dataset in chart_data['datasets']:
            assert 'borderColor' in dataset
            assert dataset['borderColor'].startswith('rgb(')
