"""
Integration tests for Django cache with Redis backend.

Validates that Django cache backend is properly configured and can
communicate with Redis for both read and write operations.
"""

import pytest
from django.core.cache import cache
from django.conf import settings


@pytest.mark.django_db
class TestDjangoCacheConfiguration:
    """Tests for Django cache backend configuration."""

    def test_cache_backend_is_redis(self):
        """Verify Django is using Redis cache backend."""
        from django.core.cache import caches

        default_cache = caches["default"]
        backend_class = default_cache.__class__.__name__

        assert "Redis" in backend_class, (
            f"Expected Redis cache backend, got: {backend_class}"
        )

    def test_cache_set_and_get(self):
        """Verify basic cache set and get operations work."""
        test_key = "test:cache:basic"
        test_value = {"ticker": "AAPL", "price": 150.50}

        # Set value in cache
        cache.set(test_key, test_value, timeout=60)

        # Retrieve value from cache
        cached_value = cache.get(test_key)

        assert cached_value == test_value

        # Cleanup
        cache.delete(test_key)

    def test_cache_ttl_constants_defined(self):
        """Verify cache TTL constants are defined in settings."""
        assert hasattr(settings, "CACHE_TTL_ALPHAVANTAGE")
        assert hasattr(settings, "CACHE_TTL_OPTIONS")

        # Verify values are correct
        assert settings.CACHE_TTL_ALPHAVANTAGE == 7 * 24 * 60 * 60  # 7 days
        assert settings.CACHE_TTL_OPTIONS == 45 * 60  # 45 minutes

    def test_cache_key_prefix_constants_defined(self):
        """Verify cache key prefix constants are defined in settings."""
        assert hasattr(settings, "CACHE_KEY_PREFIX_ALPHAVANTAGE")
        assert hasattr(settings, "CACHE_KEY_PREFIX_SCANNER")

        assert settings.CACHE_KEY_PREFIX_ALPHAVANTAGE == "alphavantage"
        assert settings.CACHE_KEY_PREFIX_SCANNER == "scanner"

    def test_cache_delete(self):
        """Verify cache delete operation works."""
        test_key = "test:cache:delete"

        cache.set(test_key, "value", timeout=60)
        assert cache.get(test_key) == "value"

        # Delete key
        cache.delete(test_key)

        # Verify key is gone
        assert cache.get(test_key) is None

    def test_cache_expiration(self):
        """Verify cache keys expire after TTL."""
        import time

        test_key = "test:cache:expiration"

        # Set with 1 second TTL
        cache.set(test_key, "expires_soon", timeout=1)

        # Value should exist immediately
        assert cache.get(test_key) == "expires_soon"

        # Wait for expiration
        time.sleep(2)

        # Value should be expired
        assert cache.get(test_key) is None

    def test_cache_get_with_default(self):
        """Verify cache.get() with default value works."""
        non_existent_key = "test:cache:nonexistent"

        result = cache.get(non_existent_key, default="default_value")

        assert result == "default_value"

    def test_cache_get_or_set(self):
        """Verify cache.get_or_set() works correctly."""
        test_key = "test:cache:get_or_set"

        # First call should set the value
        result1 = cache.get_or_set(test_key, "initial_value", timeout=60)
        assert result1 == "initial_value"

        # Second call should get cached value
        result2 = cache.get_or_set(test_key, "new_value", timeout=60)
        assert result2 == "initial_value"  # Still has original value

        # Cleanup
        cache.delete(test_key)

    def test_cache_handles_complex_types(self):
        """Verify cache can handle complex Python types."""
        from decimal import Decimal

        test_key = "test:cache:complex"
        complex_data = {
            "ticker": "AAPL",
            "intrinsic_value": Decimal("150.50"),
            "options": [
                {"strike": 145.0, "premium": 2.50},
                {"strike": 150.0, "premium": 1.75},
            ],
            "active": True,
            "count": None,
        }

        cache.set(test_key, complex_data, timeout=60)
        cached_data = cache.get(test_key)

        # Note: Decimal may be converted to float by cache serialization
        assert cached_data["ticker"] == "AAPL"
        assert float(cached_data["intrinsic_value"]) == 150.50
        assert len(cached_data["options"]) == 2
        assert cached_data["active"] is True
        assert cached_data["count"] is None

        # Cleanup
        cache.delete(test_key)

    def test_cache_clear(self):
        """Verify cache.clear() removes all keys."""
        # Set multiple test keys
        test_keys = [
            "test:cache:clear1",
            "test:cache:clear2",
            "test:cache:clear3",
        ]

        for key in test_keys:
            cache.set(key, f"value_{key}", timeout=60)

        # Verify all keys exist
        for key in test_keys:
            assert cache.get(key) is not None

        # Clear cache
        cache.clear()

        # Verify all test keys are gone
        for key in test_keys:
            assert cache.get(key) is None


@pytest.mark.django_db
class TestCacheErrorHandling:
    """Tests for cache error handling."""

    def test_cache_get_handles_none_gracefully(self):
        """Verify cache.get() returns None for missing keys without error."""
        result = cache.get("nonexistent:key:123")

        assert result is None

    def test_cache_set_with_zero_timeout(self):
        """Verify cache.set() with timeout=0 doesn't cache."""
        test_key = "test:cache:zero_timeout"

        cache.set(test_key, "value", timeout=0)

        # Should not be cached
        result = cache.get(test_key)
        assert result is None

    def test_cache_delete_nonexistent_key(self):
        """Verify cache.delete() on nonexistent key doesn't error."""
        # Should not raise exception
        cache.delete("nonexistent:key:456")
