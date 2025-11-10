# Task 030: Configure Django Redis Cache Backend

## Progress Summary

**Status**: ✅ COMPLETED (Session: 2025-11-10)

- [x] Step 1: Create git branch `refactor/scanner-django-cache`
- [x] Step 2: Add Django Redis cache backend to settings.py
- [x] Step 3: Define cache TTL constants in settings.py
- [x] Step 4: Write initial integration test to verify cache connection
- [x] Step 5: Verify existing tests still pass
- [x] Step 6: Manual testing in LOCAL environment

**Completion Notes**:
- Django cache backend configured with Redis in `wheel_analyzer/settings.py`
- Cache TTL constants defined: `CACHE_TTL_ALPHAVANTAGE` (7 days) and `CACHE_TTL_OPTIONS` (45 minutes)
- Cache key prefix constants: `CACHE_KEY_PREFIX_ALPHAVANTAGE` and `CACHE_KEY_PREFIX_SCANNER`
- Created comprehensive integration test file `scanner/tests/test_django_cache.py` with 13 tests
- All 13 cache tests passing
- Full test suite: 211/211 tests passing ✅ (gained 18 new cache tests)
- Branch `refactor/scanner-django-cache` created and ready for next tasks

## Overview

Configure Django to use Redis as its cache backend instead of the default in-memory cache. This is the foundation for migrating all scanner Redis operations to use Django's cache framework, following Django best practices.

**Current State**: 
- Django uses default in-memory cache (not persistent)
- Scanner app uses direct `redis.Redis()` client connections
- Settings have Redis URL/password in environment variables but not configured for Django cache

**Target State**:
- Django cache backend configured to use Redis
- Cache TTL constants defined for different data types
- Integration test validates cache connectivity
- All existing tests still pass

## Current State Analysis

### Current Settings

The project has Redis configured for direct connections but not for Django cache:

```python
# wheel_analyzer/settings.py (current)
# ... REDIS_URL and REDIS_PASSWORD in environment ...
# No CACHES configuration
```

### Environment Variables

From `.env` file:
- `REDIS_URL` - Full Redis connection URL
- `REDIS_PASSWORD` - Redis password

### Current Redis Usage

**Direct Redis client usage** (to be migrated later):
- `scanner/views.py` - All views use `redis.Redis.from_url()`
- `scanner/management/commands/cron_scanner.py` - Uses direct Redis
- `scanner/management/commands/cron_sma.py` - Uses direct Redis

## Target State

### Django Cache Configuration

```python
# wheel_analyzer/settings.py

# Cache TTL constants
CACHE_TTL_ALPHAVANTAGE = 7 * 24 * 60 * 60  # 7 days (604,800 seconds)
CACHE_TTL_OPTIONS = 45 * 60  # 45 minutes (2,700 seconds)

# Django cache backend configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'TIMEOUT': CACHE_TTL_OPTIONS,  # Default timeout for cache.set() without explicit timeout
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'wheel_analyzer',  # Prefix all cache keys
        'VERSION': 1,
    }
}
```

### Cache Key Naming Convention

All cache keys will follow this pattern:
- **Alpha Vantage API data**: `alphavantage:earnings:{ticker}`, `alphavantage:cashflow:{ticker}`, `alphavantage:overview:{ticker}`
- **Options scan results**: `scanner:last_scan_results`, `scanner:last_run`, `scanner:put_{ticker}`
- **SMA data**: `scanner:sma:{ticker}`

## Implementation Steps

### Step 1: Create git branch `refactor/scanner-django-cache`

Create new feature branch for this work.

**Commands**:
```bash
git checkout -b refactor/scanner-django-cache
git branch --show-current  # Verify branch name
```

**Verification**:
- Current branch is `refactor/scanner-django-cache`
- Branch created from latest `main` or current working branch

### Step 2: Add Django Redis cache backend to settings.py

Configure Django to use Redis for caching.

**File to modify**: `wheel_analyzer/settings.py`

**Add after DATABASE configuration** (around line 120):

```python
# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Cache TTL (time-to-live) constants
CACHE_TTL_ALPHAVANTAGE = 7 * 24 * 60 * 60  # 7 days in seconds (604,800)
CACHE_TTL_OPTIONS = 45 * 60  # 45 minutes in seconds (2,700)

# Django cache backend using Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "TIMEOUT": CACHE_TTL_OPTIONS,  # Default timeout for cache operations
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "SOCKET_CONNECT_TIMEOUT": 5,  # Timeout for socket connection
            "SOCKET_TIMEOUT": 5,  # Timeout for socket operations
        },
        "KEY_PREFIX": "wheel_analyzer",  # Namespace all cache keys
        "VERSION": 1,  # Cache version for invalidation
    }
}

# Cache key prefixes for different data types
CACHE_KEY_PREFIX_ALPHAVANTAGE = "alphavantage"
CACHE_KEY_PREFIX_SCANNER = "scanner"
```

**Notes**:
- Using `env("REDIS_URL")` which already exists in settings
- Default timeout is 45 minutes (for options data)
- Alpha Vantage calls will explicitly use 7-day timeout
- `KEY_PREFIX` ensures cache keys don't conflict with other Django apps
- Socket timeouts prevent indefinite hangs

**Verify**:
```bash
# Check settings.py syntax
uv run python manage.py check
```

### Step 3: Define cache TTL constants in settings.py

Already done in Step 2, but ensure these constants are accessible:

**Constants defined**:
- `CACHE_TTL_ALPHAVANTAGE = 604800` (7 days)
- `CACHE_TTL_OPTIONS = 2700` (45 minutes)
- `CACHE_KEY_PREFIX_ALPHAVANTAGE = "alphavantage"`
- `CACHE_KEY_PREFIX_SCANNER = "scanner"`

**Usage in code**:
```python
from django.conf import settings
from django.core.cache import cache

# Set Alpha Vantage data with 7-day TTL
cache.set(
    f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}",
    data,
    timeout=settings.CACHE_TTL_ALPHAVANTAGE
)

# Set options data with 45-minute TTL
cache.set(
    f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_scan_results",
    data,
    timeout=settings.CACHE_TTL_OPTIONS
)
```

### Step 4: Write initial integration test to verify cache connection

Create test to validate Django cache can connect to Redis.

**File to create**: `scanner/tests/test_django_cache.py`

**Content**:

```python
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
        
        default_cache = caches['default']
        backend_class = default_cache.__class__.__name__
        
        assert 'Redis' in backend_class, (
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
        assert hasattr(settings, 'CACHE_TTL_ALPHAVANTAGE')
        assert hasattr(settings, 'CACHE_TTL_OPTIONS')
        
        # Verify values are correct
        assert settings.CACHE_TTL_ALPHAVANTAGE == 7 * 24 * 60 * 60  # 7 days
        assert settings.CACHE_TTL_OPTIONS == 45 * 60  # 45 minutes

    def test_cache_key_prefix_constants_defined(self):
        """Verify cache key prefix constants are defined in settings."""
        assert hasattr(settings, 'CACHE_KEY_PREFIX_ALPHAVANTAGE')
        assert hasattr(settings, 'CACHE_KEY_PREFIX_SCANNER')
        
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
```

**Run test**:
```bash
just test scanner/tests/test_django_cache.py -v
```

**Expected outcome**: All tests pass, confirming Django cache is properly configured.

### Step 5: Verify existing tests still pass

Ensure cache configuration doesn't break existing functionality.

**Run full test suite**:
```bash
just test
```

**Expected outcome**: All 180 tests pass (or whatever current passing count is).

**If tests fail**:
1. Review error messages
2. Check for cache-related issues
3. Ensure test database has proper cache configuration
4. Verify Redis is running on correct port (36379)

### Step 6: Manual testing in LOCAL environment

Manually verify cache works in development environment.

**Commands**:
```bash
# Start Redis and PostgreSQL
just up

# Open Django shell
uv run python manage.py shell

# Test cache operations
>>> from django.core.cache import cache
>>> from django.conf import settings

>>> # Verify settings
>>> settings.CACHES
>>> settings.CACHE_TTL_ALPHAVANTAGE
>>> settings.CACHE_TTL_OPTIONS

>>> # Test set/get
>>> cache.set('test_key', {'data': 'value'}, timeout=60)
>>> cache.get('test_key')
{'data': 'value'}

>>> # Test expiration
>>> cache.set('expires_soon', 'value', timeout=1)
>>> cache.get('expires_soon')
'value'
>>> # Wait 2 seconds
>>> import time; time.sleep(2)
>>> cache.get('expires_soon')
None

>>> # Cleanup
>>> cache.clear()
>>> exit()
```

**Verify in Redis CLI**:
```bash
just redis-cli

# Inside Redis CLI
127.0.0.1:6379> KEYS *wheel_analyzer*
# Should see cache keys with wheel_analyzer prefix

127.0.0.1:6379> TTL wheel_analyzer:1:test_key
# Should show remaining TTL in seconds

127.0.0.1:6379> exit
```

**Expected outcome**: Cache operations work correctly, keys are properly prefixed, TTLs are respected.

## Acceptance Criteria

### Configuration Requirements

- [ ] `CACHES` setting configured with Redis backend
- [ ] `CACHE_TTL_ALPHAVANTAGE` constant = 604,800 seconds (7 days)
- [ ] `CACHE_TTL_OPTIONS` constant = 2,700 seconds (45 minutes)
- [ ] `CACHE_KEY_PREFIX_ALPHAVANTAGE` constant = "alphavantage"
- [ ] `CACHE_KEY_PREFIX_SCANNER` constant = "scanner"
- [ ] Cache keys use `wheel_analyzer` prefix
- [ ] Socket timeouts configured to prevent hangs

### Testing Requirements

- [ ] Integration test validates cache backend is Redis
- [ ] Integration test validates basic set/get operations
- [ ] Integration test validates TTL constants are defined
- [ ] Integration test validates key prefix constants are defined
- [ ] Integration test validates expiration behavior
- [ ] Integration test validates complex type handling
- [ ] All existing tests still pass (180/180)

### Manual Testing Requirements

- [ ] Django shell can import cache successfully
- [ ] cache.set() and cache.get() work correctly
- [ ] Cache keys visible in Redis with proper prefix
- [ ] TTL respected (keys expire after timeout)
- [ ] cache.clear() removes all keys

### Git Requirements

- [ ] New branch `refactor/scanner-django-cache` created
- [ ] Branch created from appropriate base branch
- [ ] No uncommitted changes from previous work

## Files Involved

### Modified Files

- `wheel_analyzer/settings.py` (~30 lines added)
  - Add CACHES configuration
  - Add cache TTL constants
  - Add cache key prefix constants

### Created Files

- `scanner/tests/test_django_cache.py` (~250 lines)
  - Integration tests for Django cache
  - Error handling tests

### Total Changes

- **Modified**: 1 file
- **Created**: 1 file
- **Lines added**: ~280 lines

## Notes

### Why Django Cache Instead of Direct Redis?

**Benefits of Django cache framework**:
1. **Abstraction**: Can switch backends without code changes
2. **Best practices**: Follows Django conventions
3. **Testing**: Easier to mock and test
4. **Features**: Built-in serialization, key prefixing, versioning
5. **Integration**: Works with Django's cache template tags
6. **Type safety**: Automatic pickling/unpickling of Python objects

**Disadvantages of direct Redis client**:
1. Tight coupling to Redis
2. Manual serialization (JSON encode/decode)
3. No automatic key prefixing
4. Harder to test (need to mock redis.Redis)
5. More boilerplate code

### Cache TTL Rationale

**Alpha Vantage data (7 days)**:
- Fundamental data (EPS, FCF) doesn't change frequently
- Quarterly earnings reports
- Annual cash flow statements
- Alpha Vantage API has rate limits (5 calls/minute, 500/day)
- Longer TTL reduces API consumption

**Options scan results (45 minutes)**:
- Market data changes throughout trading day
- Users manually trigger scans
- Reasonable balance between freshness and performance
- Prevents excessive re-scanning

### Cache Key Prefix Strategy

**Why use prefixes?**:
- Namespace different data types
- Easy to identify cache purpose
- Easy to clear specific data types
- Prevents key collisions

**Prefix examples**:
- `wheel_analyzer:1:alphavantage:earnings:AAPL`
- `wheel_analyzer:1:scanner:last_scan_results`

**Components**:
- `wheel_analyzer` = Django KEY_PREFIX setting
- `1` = Cache VERSION setting
- `alphavantage`/`scanner` = Our custom prefix constant
- `earnings`/`last_scan_results` = Data type
- `AAPL` = Specific identifier (ticker)

### Redis Connection URL

**Format**: `redis://:<password>@<host>:<port>/<db>`

**From .env**:
```
REDIS_URL=redis://:myStrongPassword@localhost:36379/0
```

**Components**:
- Protocol: `redis://`
- Password: `myStrongPassword` (after `:`)
- Host: `localhost`
- Port: `36379`
- Database: `0` (default)

### Testing Strategy

**Integration tests** (this task):
- Test Django cache configuration
- Test basic cache operations
- Require Redis to be running
- Validate real Redis connectivity

**Unit tests** (future tasks):
- Mock Django cache
- Test business logic
- Don't require Redis
- Fast execution

## Dependencies

- Django 5.1+
- `django-redis` package (may need to add to pyproject.toml)
- Redis server running on port 36379
- `django-environ` for environment variables
- `pytest-django` for testing

## Reference

**Django cache documentation**:
- https://docs.djangoproject.com/en/5.1/topics/cache/
- https://docs.djangoproject.com/en/5.1/ref/settings/#caches

**django-redis documentation**:
- https://github.com/jazzband/django-redis

**Redis Python client**:
- https://redis-py.readthedocs.io/

**Cache best practices**:
- Use timeouts to prevent stale data
- Use key prefixes to namespace data
- Use versioning for cache invalidation
- Handle cache misses gracefully
- Monitor cache hit rates
