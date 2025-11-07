# Refactors

Pending:
- None at this time

Completed:
- **API Rate Limit Optimization (Phase 4.1)** - Implemented smart stock selection in `calculate_intrinsic_value` command to respect AlphaVantage's 25 API calls/day limit. Command now processes 7 stocks by default (21 API calls, conservative), prioritizing never-calculated stocks and then oldest-calculated stocks for rolling updates. Added `--limit` and `--force-all` flags, database index on `last_calculation_date`, comprehensive API call tracking, and enhanced reporting with before/after value comparisons. Updated cron schedule from weekly to daily execution. Completed in Tasks 021-023.
- **EPS TTM Refactor** - Changed from annual EPS (OVERVIEW endpoint) to trailing twelve months EPS calculated from quarterly data (EARNINGS endpoint). Updated `calculate_intrinsic_value` management command to fetch quarterly earnings and sum the previous 4 quarters' `reportedEPS` values. This makes `current_eps` an EPS(TTM) for more accurate valuation. Updated all 35 tests in `test_calculate_intrinsic_value.py` to reflect new API call patterns (3 calls per stock instead of 2) and cache key changes.
- Add a button on the scanner page to allow the user to trigger a scan manually.
- Update the options_results.py partial or the scanner/index.html to poll the scan process and update the screen every 15 seconds when a scan is running.