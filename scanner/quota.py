"""
Quota management utilities for rate limiting.

Provides functions for checking, recording, and analyzing scan usage
against per-user daily quotas.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate

from scanner.models import ScanUsage, UserQuota

logger = logging.getLogger(__name__)


def get_todays_usage_count(user):
    """
    Return number of scans performed by user today (US/Eastern timezone).

    Uses 5-minute cache for performance. Cache key includes user ID and date.

    Args:
        user: User instance

    Returns:
        int: Count of scans performed today
    """
    # Get today's date range in US/Eastern timezone
    eastern = ZoneInfo('US/Eastern')
    now_eastern = datetime.now(eastern)
    today_start = now_eastern.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Use date string for cache key (timezone-independent)
    today_str = now_eastern.date().isoformat()
    cache_key = f"scanner:quota:{user.id}:{today_str}"

    # Try cache first
    usage_count = cache.get(cache_key)
    if usage_count is not None:
        logger.debug(f"Quota cache hit for user {user.id}: {usage_count}")
        return usage_count

    # Query database using timezone-aware range
    usage_count = ScanUsage.objects.filter(
        user=user,
        timestamp__gte=today_start,
        timestamp__lt=today_end
    ).count()

    # Cache for 5 minutes
    cache.set(cache_key, usage_count, timeout=300)
    logger.debug(f"Quota cache miss for user {user.id}, counted {usage_count}")

    return usage_count


def get_user_quota(user):
    """
    Get user's daily quota limit.

    Creates UserQuota with default limit (25) if doesn't exist.

    Args:
        user: User instance

    Returns:
        int: Daily quota limit
    """
    quota = UserQuota.get_quota_for_user(user)
    return quota.daily_limit


def get_remaining_quota(user):
    """
    Calculate remaining scans available today.

    Args:
        user: User instance

    Returns:
        int: Number of scans remaining (can be negative if over quota)
    """
    used = get_todays_usage_count(user)
    limit = get_user_quota(user)
    remaining = limit - used
    return remaining


def is_quota_exceeded(user):
    """
    Check if user has exceeded their daily quota.

    Args:
        user: User instance

    Returns:
        bool: True if quota exceeded, False otherwise
    """
    remaining = get_remaining_quota(user)
    exceeded = remaining <= 0

    if exceeded:
        logger.warning(f"User {user.id} ({user.username}) exceeded quota: {remaining} remaining")

    return exceeded


def record_scan_usage(user, scan_type, ticker=None):
    """
    Record a scan operation and invalidate cache.

    Args:
        user: User instance
        scan_type: 'curated' or 'individual'
        ticker: Stock symbol (optional, for individual scans)

    Returns:
        ScanUsage: Created record
    """
    scan_record = ScanUsage.objects.create(
        user=user,
        scan_type=scan_type,
        ticker=ticker
    )

    # Invalidate cache
    eastern = ZoneInfo('US/Eastern')
    today_str = datetime.now(eastern).date().isoformat()
    cache_key = f"scanner:quota:{user.id}:{today_str}"
    cache.delete(cache_key)

    logger.info(f"Recorded {scan_type} scan for user {user.id} (ticker: {ticker})")

    return scan_record


@transaction.atomic
def check_and_record_scan(user, scan_type, ticker=None):
    """
    Atomically check quota and record scan usage to prevent race conditions.

    This function uses database-level locking to ensure that concurrent requests
    cannot bypass quota limits. The quota check and usage recording happen within
    a single atomic transaction with row-level locking.

    Args:
        user: User instance
        scan_type: 'curated' or 'individual'
        ticker: Stock symbol (optional, for individual scans)

    Returns:
        tuple: (success: bool, scan_record: ScanUsage or None, error_message: str or None)

    Example:
        success, scan_record, error = check_and_record_scan(request.user, 'individual', 'AAPL')
        if not success:
            return HttpResponse(error, status=429)
    """
    # Lock the user's quota row for the duration of this transaction
    quota = UserQuota.objects.select_for_update().get_or_create(
        user=user,
        defaults={'daily_limit': 25}
    )[0]

    # Get today's usage within the same transaction
    eastern = ZoneInfo('US/Eastern')
    now_eastern = datetime.now(eastern)
    today_start = now_eastern.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    usage_count = ScanUsage.objects.filter(
        user=user,
        timestamp__gte=today_start,
        timestamp__lt=today_end
    ).count()

    # Check quota
    if usage_count >= quota.daily_limit:
        logger.warning(
            f"User {user.id} ({user.username}) quota exceeded: "
            f"{usage_count}/{quota.daily_limit} scans used"
        )
        return (
            False,
            None,
            f"Daily quota exceeded ({usage_count}/{quota.daily_limit} scans used)"
        )

    # Record usage
    scan_record = ScanUsage.objects.create(
        user=user,
        scan_type=scan_type,
        ticker=ticker
    )

    # Invalidate cache
    today_str = now_eastern.date().isoformat()
    cache_key = f"scanner:quota:{user.id}:{today_str}"
    cache.delete(cache_key)

    logger.info(
        f"Recorded {scan_type} scan for user {user.id} (ticker: {ticker}), "
        f"usage: {usage_count + 1}/{quota.daily_limit}"
    )

    return (True, scan_record, None)


def get_usage_history(user, days=7):
    """
    Get daily usage counts for last N days.

    Returns data suitable for Chart.js line chart.

    Args:
        user: User instance
        days: Number of days to retrieve (default: 7)

    Returns:
        dict: {
            'labels': ['2025-01-06', '2025-01-07', ...],
            'data': [5, 12, 8, ...],
        }
    """
    eastern = ZoneInfo('US/Eastern')
    today = datetime.now(eastern).date()
    start_date = today - timedelta(days=days - 1)

    # Query daily counts
    daily_counts = (
        ScanUsage.objects
        .filter(user=user, timestamp__date__gte=start_date)
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Create dict for quick lookup
    count_dict = {item['date']: item['count'] for item in daily_counts}

    # Generate labels and data for all days (fill zeros)
    labels = []
    data = []
    current_date = start_date

    while current_date <= today:
        labels.append(current_date.strftime('%Y-%m-%d'))
        data.append(count_dict.get(current_date, 0))
        current_date += timedelta(days=1)

    return {
        'labels': labels,
        'data': data,
    }


def get_next_reset_datetime():
    """
    Calculate next midnight US/Eastern timezone.

    Returns:
        datetime: Next quota reset time (midnight ET)
    """
    eastern = ZoneInfo('US/Eastern')
    now = datetime.now(eastern)

    # Get midnight at the start of tomorrow
    tomorrow = now.date() + timedelta(days=1)
    next_midnight = datetime.combine(tomorrow, datetime.min.time()).replace(tzinfo=eastern)

    return next_midnight


def get_seconds_until_reset():
    """
    Calculate seconds remaining until quota reset.

    Returns:
        int: Seconds until next midnight ET
    """
    eastern = ZoneInfo('US/Eastern')
    now = datetime.now(eastern)
    next_midnight = get_next_reset_datetime()

    delta = next_midnight - now
    return int(delta.total_seconds())
