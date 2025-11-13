"""Tests for IndividualStockScanForm.

This module tests the form validation for individual stock options scanning,
including ticker normalization, option type validation, and weeks field validation.
"""

import pytest

from scanner.forms import IndividualStockScanForm


class TestIndividualStockScanForm:
    """Tests for the IndividualStockScanForm."""

    def test_valid_form_submission(self):
        """Test that valid form submission passes validation."""
        # Arrange
        form_data = {
            'ticker': 'AAPL',
            'option_type': 'put',
            'weeks': 4,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert form.is_valid()
        assert form.cleaned_data['ticker'] == 'AAPL'
        assert form.cleaned_data['option_type'] == 'put'
        assert form.cleaned_data['weeks'] == 4

    def test_ticker_normalization_lowercase_to_uppercase(self):
        """Test that ticker is normalized to uppercase."""
        # Arrange
        form_data = {
            'ticker': 'aapl',  # lowercase
            'option_type': 'call',
            'weeks': 4,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert form.is_valid()
        assert form.cleaned_data['ticker'] == 'AAPL'  # uppercase

    @pytest.mark.parametrize("invalid_ticker,expected_error", [
        ('', 'This field is required.'),  # Empty string
        ('AAPL!', 'Ticker must contain only letters and numbers'),  # Special chars
        ('AAPL-B', 'Ticker must contain only letters and numbers'),  # Hyphen
        ('AAPL.O', 'Ticker must contain only letters and numbers'),  # Period
        ('A' * 11, 'at most 10 characters'),  # Too long (11 chars) - Django's max_length validation
        ('AA PL', 'Ticker must contain only letters and numbers'),  # Space
    ])
    def test_invalid_ticker_formats(self, invalid_ticker, expected_error):
        """Test that invalid ticker formats raise validation errors."""
        # Arrange
        form_data = {
            'ticker': invalid_ticker,
            'option_type': 'put',
            'weeks': 4,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert not form.is_valid()
        assert 'ticker' in form.errors
        assert expected_error in str(form.errors['ticker'])

    @pytest.mark.parametrize("option_type", ['put', 'call'])
    def test_option_type_validation(self, option_type):
        """Test that option type validation accepts put and call."""
        # Arrange
        form_data = {
            'ticker': 'AAPL',
            'option_type': option_type,
            'weeks': 4,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert form.is_valid()
        assert form.cleaned_data['option_type'] == option_type

    def test_option_type_invalid_choice(self):
        """Test that invalid option type raises validation error."""
        # Arrange
        form_data = {
            'ticker': 'AAPL',
            'option_type': 'invalid',
            'weeks': 4,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert not form.is_valid()
        assert 'option_type' in form.errors

    @pytest.mark.parametrize("weeks,is_valid", [
        (1, True),     # Min boundary
        (4, True),     # Default value
        (26, True),    # Mid-range
        (52, True),    # Max boundary
        (0, False),    # Below min
        (53, False),   # Above max
        (-1, False),   # Negative
    ])
    def test_weeks_field_validation(self, weeks, is_valid):
        """Test weeks field validation for boundary values."""
        # Arrange
        form_data = {
            'ticker': 'AAPL',
            'option_type': 'put',
            'weeks': weeks,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert form.is_valid() == is_valid
        if is_valid:
            assert form.cleaned_data['weeks'] == weeks

    def test_weeks_field_optional(self):
        """Test that weeks field is optional and defaults correctly."""
        # Arrange
        form_data = {
            'ticker': 'AAPL',
            'option_type': 'put',
            # weeks not provided
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert form.is_valid()
        # weeks is optional, so it should be None if not provided
        assert form.cleaned_data.get('weeks') is None

    def test_ticker_whitespace_stripped(self):
        """Test that ticker whitespace is stripped before validation."""
        # Arrange
        form_data = {
            'ticker': '  AAPL  ',  # Leading/trailing whitespace
            'option_type': 'call',
            'weeks': 4,
        }

        # Act
        form = IndividualStockScanForm(data=form_data)

        # Assert
        assert form.is_valid()
        assert form.cleaned_data['ticker'] == 'AAPL'  # No whitespace
