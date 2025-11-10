#!/usr/bin/env python3
"""
Script to update remaining Redis mocks to Django cache in scanner view tests.

This script automates the tedious process of updating test mocks from:
  - patch("scanner.views.redis.Redis.from_url")
To:
  - setup_scanner_cache() helper with Django cache

Run: python update_remaining_tests.py
"""

import re


def update_test_file():
    filepath = "scanner/tests/test_scanner_views.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Pattern 1: Simple cache setup (no options data)
    # Replace: mock_redis.keys.return_value = []
    #          mock_redis.get.return_value = b"message"
    # With: setup_scanner_cache(last_run="message")

    # Pattern 2: Cache with options data
    # Replace: mock_redis.keys.return_value = [b"put_AAPL", ...]
    #          mock_hget with json.dumps patterns
    # With: setup_scanner_cache(ticker_options={...})

    # Count patches to remove
    patches_before = len(
        re.findall(r'patch\("scanner\.views\.redis\.Redis\.from_url"\)', content)
    )

    print(f"Tests still using Redis mocks: {patches_before}")
    print("\nManual steps needed:")
    print("1. For each test with @patch('scanner.views.redis.Redis.from_url'):")
    print("   - Remove the patch decorator")
    print("   - Remove mock_redis setup code")
    print("   - Call setup_scanner_cache() with appropriate data")
    print("\n2. For tests checking scan locks:")
    print("   - Replace: mock_redis.exists(SCAN_LOCK_KEY)")
    print(
        "   - With: cache.get(f'{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress')"
    )
    print("\n3. For tests with json.dumps():")
    print("   - Remove json import and json.dumps() calls")
    print("   - Pass Python dicts directly to setup_scanner_cache()")

    # List test methods still needing updates
    test_methods_with_redis = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if 'patch("scanner.views.redis.Redis.from_url")' in line:
            # Find the test method name (look ahead for def test_)
            for j in range(max(0, i - 5), min(len(lines), i + 10)):
                if "def test_" in lines[j]:
                    test_name = lines[j].strip().split("(")[0].replace("def ", "")
                    test_methods_with_redis.append(test_name)
                    break

    print(f"\nTest methods needing updates ({len(test_methods_with_redis)}):")
    for test in test_methods_with_redis:
        print(f"  - {test}")


if __name__ == "__main__":
    update_test_file()
