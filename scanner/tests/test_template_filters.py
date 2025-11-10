"""
Unit tests for scanner template filters.

Tests the custom template filters in scanner/templatetags/options_extras.py
with focus on defensive handling of invalid input types.
"""

from decimal import Decimal
from scanner.templatetags.options_extras import dict_get, lookup, check_good_options


class TestDictGetFilter:
    """Tests for the dict_get template filter."""

    def test_dict_get_with_valid_dict(self):
        """dict_get returns value when given valid dictionary and key."""
        test_dict = {"AAPL": "Apple", "MSFT": "Microsoft"}

        result = dict_get(test_dict, "AAPL")

        assert result == "Apple"

    def test_dict_get_with_missing_key(self):
        """dict_get returns None when key not in dictionary."""
        test_dict = {"AAPL": "Apple"}

        result = dict_get(test_dict, "MSFT")

        assert result is None

    def test_dict_get_with_none(self):
        """dict_get returns None when dictionary is None."""
        result = dict_get(None, "AAPL")

        assert result is None

    def test_dict_get_with_empty_string(self):
        """dict_get returns None when given empty string (THE BUG CASE)."""
        result = dict_get("", "AAPL")

        assert result is None

    def test_dict_get_with_non_empty_string(self):
        """dict_get returns None when given non-empty string."""
        result = dict_get("invalid_string", "AAPL")

        assert result is None

    def test_dict_get_with_integer(self):
        """dict_get returns None when given integer."""
        result = dict_get(42, "AAPL")

        assert result is None

    def test_dict_get_with_list(self):
        """dict_get returns None when given list."""
        result = dict_get(["item1", "item2"], "AAPL")

        assert result is None

    def test_dict_get_with_empty_dict(self):
        """dict_get returns None when key not in empty dict."""
        result = dict_get({}, "AAPL")

        assert result is None

    def test_dict_get_logs_warning_for_invalid_type(self, caplog):
        """dict_get logs warning when receiving non-dict type."""
        import logging

        with caplog.at_level(logging.WARNING):
            dict_get("invalid", "key")

        assert "dict_get received non-dict type" in caplog.text
        assert "str" in caplog.text


class TestLookupFilter:
    """Tests for the lookup template filter."""

    def test_lookup_with_valid_dict(self):
        """lookup returns value when given valid dictionary and key."""
        test_dict = {"AAPL": "Apple", "MSFT": "Microsoft"}

        result = lookup(test_dict, "MSFT")

        assert result == "Microsoft"

    def test_lookup_with_none(self):
        """lookup returns None when dictionary is None."""
        result = lookup(None, "AAPL")

        assert result is None

    def test_lookup_with_invalid_type(self):
        """lookup returns None when given non-dict type."""
        result = lookup("invalid", "AAPL")

        assert result is None

    def test_lookup_consistency_with_dict_get(self):
        """lookup and dict_get behave consistently."""
        test_dict = {"AAPL": "Apple"}

        lookup_result = lookup(test_dict, "AAPL")
        dict_get_result = dict_get(test_dict, "AAPL")

        assert lookup_result == dict_get_result


class TestCheckGoodOptionsTag:
    """Tests for the check_good_options template tag."""

    def test_check_good_options_with_good_option(self):
        """check_good_options returns True when option strike <= IV."""
        options = [
            {"strike": 140.0, "price": 2.5},
            {"strike": 145.0, "price": 2.0},
        ]
        intrinsic_value = Decimal("150.00")

        result = check_good_options(options, intrinsic_value)

        assert result is True

    def test_check_good_options_with_no_good_options(self):
        """check_good_options returns False when all strikes > IV."""
        options = [
            {"strike": 155.0, "price": 2.5},
            {"strike": 160.0, "price": 2.0},
        ]
        intrinsic_value = Decimal("150.00")

        result = check_good_options(options, intrinsic_value)

        assert result is False

    def test_check_good_options_with_none_iv(self):
        """check_good_options returns False when IV is None."""
        options = [{"strike": 140.0, "price": 2.5}]

        result = check_good_options(options, None)

        assert result is False

    def test_check_good_options_with_empty_list(self):
        """check_good_options returns False when options list is empty."""
        result = check_good_options([], Decimal("150.00"))

        assert result is False

    def test_check_good_options_with_exact_match(self):
        """check_good_options returns True when strike equals IV."""
        options = [{"strike": 150.0, "price": 2.5}]
        intrinsic_value = Decimal("150.00")

        result = check_good_options(options, intrinsic_value)

        assert result is True
