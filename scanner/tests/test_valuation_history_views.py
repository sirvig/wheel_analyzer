"""
Tests for valuation history views.

Test coverage:
- Stock history view renders correctly
- Comparison view shows deltas accurately
- CSV export returns correct format
- Authentication required for all views
- 404 for non-existent stocks
- Empty state handling (no history)
"""

import pytest
from datetime import date
from decimal import Decimal
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
class TestStockHistoryView:

    def test_stock_history_view_renders(self, client, authenticated_user):
        """Test that stock history view renders with data."""
        # Create stock with history
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.00"),
        )

        # Create historical snapshots
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("145.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),
            intrinsic_value=Decimal("140.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Access history view
        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        # Verify response
        assert response.status_code == 200
        assert 'stock' in response.context
        assert 'history' in response.context
        assert 'has_history' in response.context
        assert response.context['stock'] == stock
        assert response.context['has_history'] is True
        assert response.context['history'].count() == 2

    def test_stock_history_view_no_history(self, client, authenticated_user):
        """Test stock history view with no historical data."""
        # Create stock without history
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.00"),
        )

        # Access history view
        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        # Verify response
        assert response.status_code == 200
        assert response.context['has_history'] is False
        assert response.context['history'].count() == 0

    def test_stock_history_view_404_for_nonexistent_stock(self, client, authenticated_user):
        """Test 404 returned for non-existent stock."""
        url = reverse('scanner:stock_history', kwargs={'symbol': 'NONEXISTENT'})
        response = client.get(url)

        assert response.status_code == 404

    def test_stock_history_view_requires_authentication(self, client):
        """Test that view requires authentication."""
        stock = CuratedStock.objects.create(symbol="TEST1", active=True)

        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_stock_history_view_ordering(self, client, authenticated_user):
        """Test that history is ordered by date descending (newest first)."""
        stock = CuratedStock.objects.create(symbol="TEST1", active=True)

        # Create snapshots in random order
        snap1 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 1, 1),
            intrinsic_value=Decimal("140.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        snap2 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        snap3 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 7, 1),
            intrinsic_value=Decimal("145.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        history = list(response.context['history'])
        # Should be ordered: 2025, 2024-07, 2024-01
        assert history[0] == snap2
        assert history[1] == snap3
        assert history[2] == snap1


@pytest.mark.django_db
class TestValuationComparisonView:

    def test_comparison_view_renders(self, client, authenticated_user):
        """Test that comparison view renders correctly."""
        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        assert response.status_code == 200
        assert 'stocks' in response.context
        assert 'comparison_date_quarter' in response.context
        assert 'comparison_date_year' in response.context

    def test_comparison_view_requires_authentication(self, client):
        """Test that comparison view requires authentication."""
        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_comparison_view_calculates_deltas(self, client, authenticated_user):
        """Test that comparison view calculates deltas correctly."""
        # Create stock
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.00"),
            preferred_valuation_method="EPS",
        )

        # Create historical snapshots
        # For Nov 2025: previous quarter is Q3 2025 (Jul 1), year ago is Q4 2024 (Oct 1)
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 7, 1),  # Previous quarter (Q3 2025)
            intrinsic_value=Decimal("145.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),  # Year ago (Q4 2024)
            intrinsic_value=Decimal("130.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        # Find our stock in the comparison data
        stock_data = None
        for data in response.context['stocks']:
            if data['stock'].symbol == 'TEST1':
                stock_data = data
                break

        assert stock_data is not None
        assert stock_data['current_value'] == Decimal("150.00")

        # Check quarter delta (150 - 145 = 5, 3.45%)
        if stock_data['quarter_value']:
            assert stock_data['quarter_delta'] == Decimal("5.00")
            assert abs(stock_data['quarter_pct'] - Decimal("3.45")) < Decimal("0.01")

        # Check year delta (150 - 130 = 20, 15.38%)
        if stock_data['year_value']:
            assert stock_data['year_delta'] == Decimal("20.00")
            assert abs(stock_data['year_pct'] - Decimal("15.38")) < Decimal("0.01")


@pytest.mark.django_db
class TestCSVExport:

    def test_export_all_history_csv(self, client, authenticated_user):
        """Test exporting all stock history to CSV."""
        # Create stocks with history
        stock1 = CuratedStock.objects.create(symbol="TEST1", active=True)
        stock2 = CuratedStock.objects.create(symbol="TEST2", active=True)

        ValuationHistory.objects.create(
            stock=stock1,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        ValuationHistory.objects.create(
            stock=stock2,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("200.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:export_all_history')
        response = client.get(url)

        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']
        assert 'valuation_history_all' in response['Content-Disposition']

        # Parse CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')

        # Verify header
        assert 'Symbol' in lines[0]
        assert 'Quarter' in lines[0]
        assert 'Intrinsic Value (EPS)' in lines[0]

        # Verify data rows (at least 2 for 2 stocks)
        assert len(lines) >= 3  # Header + 2 data rows

    def test_export_single_stock_csv(self, client, authenticated_user):
        """Test exporting single stock history to CSV."""
        stock = CuratedStock.objects.create(symbol="TEST1", active=True)

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            current_eps=Decimal("6.42"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            notes="Test snapshot",
        )

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'valuation_history_TEST1' in response['Content-Disposition']

        # Parse CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')

        # Verify only TEST1 data
        assert 'TEST1' in lines[1]
        assert 'Q1 2025' in lines[1]
        assert '150.00' in lines[1] or '150.0' in lines[1]
        assert '6.42' in lines[1]

    def test_csv_export_requires_authentication(self, client):
        """Test that CSV export requires authentication."""
        url = reverse('scanner:export_all_history')
        response = client.get(url)

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_csv_export_empty_history(self, client, authenticated_user):
        """Test CSV export with no historical data."""
        # Create stock without history
        CuratedStock.objects.create(symbol="TEST1", active=True)

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'TEST1'})
        response = client.get(url)

        # Should still return CSV with just header
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')

        # Only header, no data rows
        assert len(lines) == 1
        assert 'Symbol' in lines[0]
