# Refactors

Pending:
- None at this time

Completed:
- **EPS TTM Refactor** - Changed from annual EPS (OVERVIEW endpoint) to trailing twelve months EPS calculated from quarterly data (EARNINGS endpoint). Updated `calculate_intrinsic_value` management command to fetch quarterly earnings and sum the previous 4 quarters' `reportedEPS` values. This makes `current_eps` an EPS(TTM) for more accurate valuation. Updated all 35 tests in `test_calculate_intrinsic_value.py` to reflect new API call patterns (3 calls per stock instead of 2) and cache key changes.
- Add a button on the scanner page to allow the user to trigger a scan manually.
- Update the options_results.py partial or the scanner/index.html to poll the scan process and update the screen every 15 seconds when a scan is running.