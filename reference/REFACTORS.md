# Refactors

Pending:

Completed:
- ✅ **LOCAL Environment Market Hours Bypass** - Implemented ability to run options scans outside market hours when `ENVIRONMENT=LOCAL`. This development-only feature allows testing and debugging the scanner functionality without waiting for market hours (9:30 AM - 4:00 PM ET). The scanner now checks `settings.ENVIRONMENT` and passes `debug=True` to `perform_scan()` when in LOCAL mode, bypassing the `is_market_open()` check. Added amber warning banners to both `scan_polling.html` and `options_results.html` to alert developers that data may be stale when scans run outside market hours. Created `.env.example` with ENVIRONMENT documentation. Added comprehensive tests to verify LOCAL bypass behavior and PRODUCTION enforcement.
  - **Files Changed**:
    - Modified: `wheel_analyzer/settings.py` (added `ENVIRONMENT` setting with default "PRODUCTION")
    - Modified: `scanner/views.py` (added environment check in `run_scan_in_background()`, added `is_local_environment` to context)
    - Modified: `templates/scanner/partials/scan_polling.html` (added development mode warning banner, conditional market hours note)
    - Modified: `templates/scanner/partials/options_results.html` (added development mode warning banner, conditional market hours note)
    - Created: `.env.example` (documented all environment variables including ENVIRONMENT)
    - Modified: `scanner/tests/test_scanner_views.py` (added 2 tests for LOCAL and PRODUCTION environment behaviors)
  - **Environment Values**:
    - `LOCAL`: Development environment, bypasses market hours check for manual scans
    - `TESTING`: Test environment (automatically set by pytest)
    - `PRODUCTION`: Production environment, enforces market hours restrictions (default)
  - **How it works**: When the "Scan for Options" button is clicked, `scan_view()` calls `run_scan_in_background()` which checks `settings.ENVIRONMENT`. If set to "LOCAL", it passes `debug=True` to `perform_scan()`, causing the scanner to skip the `is_market_open()` check. Templates display an amber warning banner when `is_local_environment` context variable is True, informing developers the data may be stale.

- ✅ **Preferred Valuation Highlighting** - Updated `/scanner/valuations/` table to visually highlight the preferred intrinsic value method for at-a-glance visibility. Preferred IV cells now feature method-specific background colors (blue for EPS, cyan for FCF), bold font weight, and enhanced contrast in both light and dark modes. Non-preferred values are dimmed (gray text) to reduce visual noise. This allows users to quickly identify the valuation number that matters most for each stock without needing to reference the "Preferred" column.
  - **Files Changed**:
    - Modified: `templates/scanner/valuations.html` (added conditional CSS classes to IV cells)
  - **Visual Design**:
    - EPS preferred: `bg-blue-50 dark:bg-blue-900/20` + `font-semibold` on value
    - FCF preferred: `bg-cyan-50 dark:bg-cyan-900/20` + `font-semibold` on value
    - Non-preferred: `text-gray-400` (dimmed appearance)
  - **How it works**: Template conditionally applies Tailwind CSS classes based on `stock.preferred_valuation_method`. The preferred cell gets a subtle background tint matching the badge color scheme, bold text, and full contrast. The non-preferred cell's value is rendered in gray to de-emphasize it.
- **API Rate Limit Optimization (Phase 4.1)** - Implemented smart stock selection in `calculate_intrinsic_value` command to respect AlphaVantage's 25 API calls/day limit. Command now processes 7 stocks by default (21 API calls, conservative), prioritizing never-calculated stocks and then oldest-calculated stocks for rolling updates. Added `--limit` and `--force-all` flags, database index on `last_calculation_date`, comprehensive API call tracking, and enhanced reporting with before/after value comparisons. Updated cron schedule from weekly to daily execution. Completed in Tasks 021-023.
- **EPS TTM Refactor** - Changed from annual EPS (OVERVIEW endpoint) to trailing twelve months EPS calculated from quarterly data (EARNINGS endpoint). Updated `calculate_intrinsic_value` management command to fetch quarterly earnings and sum the previous 4 quarters' `reportedEPS` values. This makes `current_eps` an EPS(TTM) for more accurate valuation. Updated all 35 tests in `test_calculate_intrinsic_value.py` to reflect new API call patterns (3 calls per stock instead of 2) and cache key changes.
- Add a button on the scanner page to allow the user to trigger a scan manually.
- Update the options_results.py partial or the scanner/index.html to poll the scan process and update the screen every 15 seconds when a scan is running.