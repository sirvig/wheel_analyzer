# Wheel-Analyzer Development Roadmap

Wheel Analyzer is a Django-based web application for tracking and analyzing stock options trading, specifically focused on the "wheel strategy" (selling puts, taking assignment, selling calls). The application helps track options campaigns, individual transactions, and scan for new trading opportunities.

## Overview

Wheel Analyzer looks through a curated list of stocks, finds their options for a given time period and analyzes them, looking for options that provide a 30% or greater annualized return with a delta of less than .20 or -.20

## Development Workflow

1. **Task Planning**

- Study the existing codebase and understand the current state
- Update `ROADMAP.md` to include the new task
- Priority tasks should be inserted after the last completed task

2. **Task Creation**

- Study the existing codebase and understand the current state
- Create a new task file in the `/tasks` directory
- Name format: `XXX-description.md` (e.g., `001-db.md`)
- Include high-level specifications, relevant files, acceptance criteria, and implementation steps
- Refer to last completed task in the `/tasks` directory for examples. For example, if the current task is `012`, refer to `011` and `010` for examples.
- Note that these examples are completed tasks, so the content reflects the final state of completed tasks (checked boxes and summary of changes). For the new task, the document should contain empty boxes and no summary of changes. Refer to `000-sample.md` as the sample for initial state.

3. **Task Implementation**

- Follow the specifications in the task file
- Implement features and functionality
- Update step progress within the task file after each step
- Stop after completing each step and wait for further instructions

4. **Roadmap Updates**

- Mark completed tasks with ✅ in the roadmap
- Add reference to the task file (e.g., `See: /tasks/001-db.md`)

## Task Files

Detailed implementation tasks are tracked in the `/tasks` directory:


## Development Phases

### Phase 1: Curated Stock List

**Status**: ✅ Completed

**Related Tasks**:

- ✅ `001-curated-stock-model.md` - Created CuratedStock Django model with admin interface
- ✅ `002-data-migration.md` - Migrated 26 stocks from JSON to database
- ✅ `003-update-scanner.md` - Updated scanner commands to use database model

**Summary**:
Successfully migrated from JSON-based stock management to a database-driven CuratedStock model. The scanner commands (`cron_sma` and `cron_scanner`) now query active stocks from the database, enabling dynamic stock management through the Django admin interface. All 26 stocks were successfully imported and verified. See task files for detailed implementation notes.

### Phase 2: Manual Scan Trigger

**Status**: ✅ Completed

**Related Tasks**:

- ✅ `004-refactor-scan-logic.md` - Refactored core scan logic into a reusable function
- ✅ `005-backend-scan-view.md` - Implemented backend view and URL for manual scanning
- ✅ `006-frontend-scan-button.md` - Added button to the frontend to trigger the scan

**Summary**:
Successfully implemented manual scan functionality for the scanner page. Users can now trigger an on-demand options scan by clicking the "Scan for Options" button. The implementation includes:
- Extracted core scanning logic from `cron_scanner` management command into reusable `perform_scan()` function in `scanner/scanner.py`
- Created Django view with Redis locking mechanism (10-minute timeout) to prevent concurrent scans
- Added HTMX-powered button with loading indicator for seamless user experience
- Created dedicated partial template (`scanner/partials/options_results.html`) for HTMX updates
- Comprehensive error handling with user-friendly messages for different scenarios (scan in progress, market closed, errors)
See task files for detailed implementation notes.

### Phase 3: Polling for Scan Progress

**Status**: ✅ Completed

**Related Tasks**:

- ✅ `007-async-scan-view.md` - Refactor scan view for asynchronous execution
- ✅ `008-polling-status-endpoint.md` - Create polling status endpoint
- ✅ `009-frontend-polling-trigger.md` - Update frontend to trigger polling

**Summary**:
Successfully implemented a polling mechanism with progressive results display for the manual options scan feature. Users now see real-time feedback as the scan progresses, with options appearing as they're found. The implementation includes:
- Refactored `scan_view` to execute scans in background threads using Python's `threading` module
- Created `scan_status` polling endpoint that returns updated results every 15 seconds
- Built `scan_polling.html` template with animated status banner showing progress percentage
- Progressive results display: users see options appearing in real-time as each ticker is scanned
- Error handling: error messages from scan failures display in the status area
- Multi-user support: multiple users can watch the same scan progress simultaneously
- Graceful polling termination: when scan completes, polling automatically stops and final results display
- HTMX-powered frontend with `outerHTML` swap for seamless state transitions
See task files for detailed implementation notes.

### Phase 4: Calculate fair value for stocks in the curated list

**Status**: ✅ Completed (Including FCF Enhancement)

**Related Tasks**:

- ✅ `013-add-intrinsic-value-fields.md` - Add database fields to CuratedStock model for intrinsic value and DCF assumptions
- ✅ `014-dcf-calculation-functions.md` - Create DCF calculation utility functions (EPS-based)
- ✅ `015-valuation-management-command.md` - Create weekly management command to calculate intrinsic values
- ⏳ `016-valuation-testing.md` - Add comprehensive unit and integration tests (optional enhancement)

**Summary**:
Successfully implemented a weekly valuation system that calculates the intrinsic value (fair value) of stocks in the curated list using an EPS-based Discounted Cash Flow (DCF) model. The system:

**✅ Completed Implementation**:

1. **Database Schema** (Task 013):
   - Added 7 new fields to CuratedStock model
   - Calculation results: `intrinsic_value`, `last_calculation_date`
   - DCF assumptions: `current_eps`, `eps_growth_rate` (10%), `eps_multiple` (20), `desired_return` (15%), `projection_years` (5)
   - Django admin interface updated with organized fieldsets

2. **DCF Calculation Engine** (Task 014):
   - Created `scanner/valuation.py` module with complete DCF logic
   - Functions: `project_eps()`, `calculate_terminal_value()`, `discount_to_present_value()`, `discount_eps_series()`, `calculate_intrinsic_value()`
   - Uses Python Decimal type for financial precision
   - Comprehensive logging and error handling
   - **21 unit tests - all passing ✅**

3. **Management Command** (Task 015):
   - Created `calculate_intrinsic_value` command
   - Fetches EPS TTM from Alpha Vantage EARNINGS endpoint (sum of 4 quarterly reportedEPS)
   - Also fetches OVERVIEW and CASH_FLOW endpoints for complete valuation data
   - Redis caching with 7-day TTL
   - 20-second rate limiting (3 calls/minute) for conservative API usage
   - Command options: `--symbols`, `--force-refresh`, `--clear-cache`
   - Comprehensive error handling and logging
   - Summary statistics output
   - **Note**: Refactored from annual EPS to trailing twelve months (TTM) for more accurate valuation

**DCF Formula Implemented**:
```
Projected EPS[year] = Current EPS × (1 + growth_rate)^year
Terminal Value = Projected EPS[Year 5] × EPS Multiple
PV of EPS[year] = Projected EPS[year] / (1 + desired_return)^year
PV of Terminal = Terminal Value / (1 + desired_return)^5
Intrinsic Value = Sum(PV of all Projected EPS) + PV of Terminal Value
```

**Usage**:
```bash
# Calculate for all active stocks
python manage.py calculate_intrinsic_value

# Calculate for specific stocks
python manage.py calculate_intrinsic_value --symbols AAPL MSFT

# Force refresh cached API data
python manage.py calculate_intrinsic_value --force-refresh

# Schedule daily (8 PM Eastern) - Updated in Phase 4.1
0 20 * * * cd /path/to/project && python manage.py calculate_intrinsic_value
```

**Completed Tasks**:
- ✅ `016-valuation-testing.md` - Enhanced valuation testing with 11 unit tests and 8 integration tests
- ✅ `017-add-fcf-fields.md` - Added FCF fields to CuratedStock model for dual valuation approach
- ✅ `018-fcf-calculation-functions.md` - Created FCF-based DCF calculation functions
- ✅ `019-fcf-management-command.md` - Updated management command to support both EPS and FCF calculations
- ✅ `020-fcf-testing.md` - Added comprehensive tests for FCF calculations (8 integration tests)

**FCF-based DCF Enhancement** (✅ Completed):

The system now supports both EPS-based and FCF-based DCF valuation methods:

**Database Schema** (Task 017):
- Added 5 new fields to CuratedStock model
- `intrinsic_value_fcf` - FCF-based calculated value
- `current_fcf_per_share` - TTM FCF per share
- `fcf_growth_rate` - FCF growth assumption (default: 10%)
- `fcf_multiple` - FCF terminal value multiple (default: 20)
- `preferred_valuation_method` - User choice between EPS/FCF (default: EPS)
- Migration `0005_add_fcf_fields.py` applied successfully

**Calculation Functions** (Task 018):
- Added 4 new FCF calculation functions to `scanner/valuation.py`
- `calculate_fcf_from_quarters()` - Calculates TTM FCF from Alpha Vantage quarterly data
- `calculate_fcf_per_share()` - Divides TTM FCF by shares outstanding
- `project_fcf()` - Projects future FCF using compound growth
- `calculate_intrinsic_value_fcf()` - Complete FCF-based DCF calculation
- 24 unit tests added - all passing

**Management Command** (Task 019):
- Updated `calculate_intrinsic_value` command for dual calculations
- Fetches EARNINGS (quarterly EPS), OVERVIEW (shares outstanding), and CASH_FLOW (quarterly FCF) from Alpha Vantage
- **3 API calls per stock**: EARNINGS for EPS TTM, OVERVIEW for shares, CASH_FLOW for FCF TTM
- Independent success/failure tracking for EPS and FCF methods
- Rate limiting: 20 seconds (3 calls/minute) for conservative Alpha Vantage API usage
- Separate statistics in summary output for each method
- Cache management with separate keys: `av_earnings_{symbol}`, `av_overview_{symbol}`, `av_cashflow_{symbol}`

**Testing** (Task 020):
- 8 new FCF integration tests added
- Tests cover dual calculation, negative FCF handling, cache behavior, and error scenarios
- Total test coverage: 56 unit tests + 40 integration tests = 96 tests passing
- All tests updated for EPS TTM refactor (EARNINGS endpoint instead of OVERVIEW for EPS)

**Usage**:
```bash
# Calculate both EPS and FCF intrinsic values for all active stocks
python manage.py calculate_intrinsic_value

# View both values in Django admin
# Users can set preferred_valuation_method per stock (EPS or FCF)
```

**Remaining Tasks** (Optional Enhancements):
- Performance tests, live API tests, and coverage analysis can be added if needed (see Task 016 for details)
- Test database isolation fixes for integration tests (optional)

See task files for detailed implementation notes.

### Phase 4.1: API Rate Limit Optimization for Intrinsic Value Calculations

**Status**: ✅ Completed

**Related Tasks**:

- ✅ `021-add-calculation-date-index.md` - Add database index on last_calculation_date for query performance
- ✅ `022-smart-stock-selection.md` - Implement smart stock selection logic prioritizing never-calculated and oldest stocks
- ✅ `023-api-call-tracking.md` - Add API call tracking and enhanced reporting with before/after values

**Summary**:
Successfully optimized the `calculate_intrinsic_value` management command to respect AlphaVantage's free tier limit of 25 API requests per day. The system makes 3 API calls per stock (EARNINGS, OVERVIEW, CASH_FLOW), and now implements a rolling update strategy that:

- Processes 7 stocks per run (21 API calls, conservative limit) by default
- Prioritizes stocks that have never been calculated (NULL `last_calculation_date`)
- Then processes stocks with the oldest `last_calculation_date` (stale valuations)
- Added `--limit N` flag to override the default 7-stock limit
- Added `--force-all` flag to process all stocks (with API limit warning)
- Implements detailed logging with before/after intrinsic values for both EPS and FCF methods
- Tracks API calls made vs cached responses with cache hit rate reporting
- Displays remaining stocks needing calculation in summary
- Designed for daily cron execution for rolling updates instead of weekly batches

**Technical Implementation**:
- Added database index on `last_calculation_date` (migration 0006) for efficient queries
- Smart QuerySet selection: prioritize NULL dates, then order by oldest first
- Instance-level counters for API calls and cache hits in all three fetch methods
- Enhanced per-stock output showing previous and new values with delta/percentage change
- Pre-execution summary showing total stocks, never-calculated count, and API call estimates
- Post-execution summary with API usage stats and remaining work statistics
- 20-second rate limiting (3 calls/minute) for conservative API usage

**Completed Tasks**:
- ✅ Task 021: Created database migration adding B-tree index on `last_calculation_date`
- ✅ Task 022: Implemented smart stock selection with `--limit` and `--force-all` flags, plus detailed pre-execution summary
- ✅ Task 023: Added comprehensive API call tracking and enhanced reporting with before/after value comparisons

**Expected Outcome**:
All curated stocks stay up-to-date with intrinsic valuations through daily rolling updates (7 stocks/day = full portfolio refresh every ~7 days for 50 stocks), respecting API rate limits while maintaining calculation freshness across the portfolio. Cache hit rates reduce actual API calls significantly over time.

### Phase 5: Update Option Scanner to provide a visual representation of intrinsic value

**Status**: ✅ Completed

**Related Tasks**:

- ✅ `024-add-intrinsic-value-context.md` - Add intrinsic value context to scanner views
- ✅ `025-add-visual-indicators.md` - Update options results template with Tailwind CSS badges
- ✅ `026-valuation-page-backend.md` - Create backend view and URL for valuations page
- ✅ `027-valuation-page-frontend.md` - Create frontend template and navbar navigation
- ⏳ `028-testing-and-refinement.md` - Add comprehensive tests and perform manual testing (tests pending)
- ✅ `029-fix-redis-timeout-bug.md` - Fix 'str' object has no attribute 'get' error when Redis data expires

**Summary**:
Successfully added visual indicators to the options scanner showing whether option strike prices are at or below intrinsic value, and created a comprehensive valuations page for the curated stock list.

**Visual Indicators Feature**:
- Tailwind CSS badges on each option row showing comparison to intrinsic value
  - Green "✓ Good": Strike ≤ Intrinsic Value (would buy at/below fair value if assigned)
  - Red "✗ High": Strike > Intrinsic Value (would buy above fair value if assigned)
  - Yellow "⚠ N/A": Intrinsic Value not calculated (NULL)
- Badge on accordion header showing overall stock status
  - Green ✓: At least one option has strike ≤ IV
  - Red ✗: All options have strike > IV
  - Yellow ⚠: No intrinsic value calculated
- Uses `preferred_valuation_method` to choose between EPS and FCF intrinsic values
- Template filters and tags: `dict_get` for dictionary access, `check_good_options` for status detection

**Valuations Page Feature**:
- New page at `/scanner/valuations/` displaying all active curated stocks
- Responsive Tailwind CSS table with columns:
  - Ticker and Company Name
  - Intrinsic Value (EPS) and Intrinsic Value (FCF)
  - Preferred Valuation Method (badge indicator)
  - Last Calculation Date
  - Key Assumptions (growth rates, multiples, desired return)
- Graceful handling of NULL intrinsic values (shows "-" or "Never")
- Authentication required (@login_required)
- Stocks ordered alphabetically by ticker
- Accessible via navbar dropdown menu ("Scanner" → "Stock Valuations")

**Technical Implementation**:
- `CuratedStock.get_effective_intrinsic_value()` model method returns IV based on preferred method
- Scanner views (`scan_view`, `scan_status`) include `curated_stocks` dictionary in context
- Custom template filter `dict_get` for dictionary access in Django templates
- Custom template tag `check_good_options` to determine accordion header badge color
- `valuation_list_view` Django view with queryset filtering and ordering
- Tailwind CSS with Flowbite components for styling
- Responsive design with proper mobile support

**Completed Tasks**:
- ✅ Task 024: Added `get_effective_intrinsic_value()` method and updated scanner views context
- ✅ Task 025: Converted options display from list to table format with status badges
- ✅ Task 026: Created backend view and URL routing for valuations page
- ✅ Task 027: Created frontend template with Tailwind table and navbar dropdown menu

**Remaining Work**:
- Unit tests for `get_effective_intrinsic_value()` method
- Integration tests for `valuation_list_view`
- Integration tests for scanner view context
- Manual testing of visual indicators and responsive design

**Bug Fixes** (Task 029):
- Fixed Redis timeout bug causing `'str' object has no attribute 'get'` error
- Implemented hybrid defense-in-depth approach:
  - Backend validation with Redis error handling
  - Defensive template filter with type checking
  - Enhanced logging for debugging
- Comprehensive unit and integration tests with Redis mocks
- Graceful degradation when Redis data unavailable (shows gray "-" badges)
- User-friendly error messages ("Data temporarily unavailable")

See task files for detailed implementation notes.

### Phase 5.1: Cache Migration to Django Framework

**Status**: ✅ Completed

**Related Tasks**:

- ✅ `030-configure-django-redis-cache.md` - Configure Django cache framework with Redis backend
- ✅ `031-refactor-alphavantage-to-django-cache.md` - Migrate Alpha Vantage API caching
- ✅ `032-refactor-scanner-views-to-django-cache.md` - Migrate scanner views caching
- ✅ `033-update-management-commands-django-cache.md` - Update management commands
- ✅ `034-final-testing-and-cleanup.md` - Final validation and documentation

**Summary**:
Successfully migrated the scanner application from direct Redis usage to Django's cache framework with Redis backend. This migration improves code maintainability, testability, and follows Django best practices.

**Migration Details**:

**From (Direct Redis)**:
- Manual `redis.Redis.from_url()` client creation
- Manual JSON serialization with `json.loads/dumps`
- Inconsistent cache key naming
- No automatic TTL support
- Difficult to test (requires Redis instance)
- Tight coupling to Redis implementation

**To (Django Cache Framework)**:
- Django cache backend: `django.core.cache.backends.redis.RedisCache`
- Automatic serialization (handles complex Python types)
- Consistent cache key prefixing (`wheel_analyzer:1:*`)
- Built-in TTL support via `timeout` parameter
- Easy to test (mock `cache` object)
- Framework abstraction (can switch backends easily)

**Cache Configuration**:
- **Alpha Vantage API data**: 7-day TTL (604,800 seconds)
  - Cache keys: `alphavantage:earnings:{symbol}`, `alphavantage:cashflow:{symbol}`, `alphavantage:overview:{symbol}`
  - Purpose: Minimize API consumption (Alpha Vantage limit: 25 calls/day)
  
- **Options scan data**: 45-minute TTL (2,700 seconds)
  - Cache keys: `scanner:ticker_options`, `scanner:last_run`, `scanner:scan_in_progress`
  - Purpose: Balance market data freshness with performance

**Files Migrated**:
- `scanner/alphavantage/util.py` - Alpha Vantage API caching
- `scanner/alphavantage/technical_analysis.py` - SMA calculations caching
- `scanner/views.py` - Scanner views caching
- `scanner/management/commands/cron_scanner.py` - Scan command caching
- `scanner/management/commands/calculate_intrinsic_value.py` - Removed old cache keys

**Testing Improvements**:
- Added 40+ new cache tests across 7 test files
- Fixed 5 pre-existing cache tests with correct mock patterns
- Mock `requests.get` (HTTP layer) instead of `get_market_data` to properly test caching
- All 216 tests passing (180 scanner + 36 tracker)

**Performance Results**:
- **17x faster** on cache hits (0.87s → 0.05s)
- 100% cache hit rate on subsequent runs
- Zero unnecessary API calls after initial data fetch
- Intrinsic value calculations benefit most (3 API calls → 0)

**Error Handling**:
- All cache operations wrapped in try/except blocks
- Graceful degradation if Redis unavailable (app continues working)
- Cache failures logged at WARNING level
- Views return safe defaults (empty dicts) on cache errors

**Documentation**:
- Added comprehensive Caching section to AGENTS.md
- Usage patterns with code examples
- Error handling approach documented
- Manual Redis CLI operations for debugging
- Testing strategy documented

**Code Quality**:
- No direct Redis usage (`import redis` removed)
- No unused cache imports
- Linting verified with ruff
- Production-ready code

**Completed Tasks**:
- ✅ Task 030: Django cache configuration with environment variables
- ✅ Task 031: Alpha Vantage caching refactor (15 unit tests added)
- ✅ Task 032: Scanner views caching refactor (10 integration tests added)
- ✅ Task 033: Management commands updated with cache cleanup
- ✅ Task 034: Final testing, performance validation, documentation

**Project Impact**:
- ~1,500 lines changed across 15 files
- 40+ new tests for comprehensive cache coverage
- 17x performance improvement on cache hits
- Better code maintainability and testability
- Follows Django framework best practices

See task files and AGENTS.md for detailed implementation notes.

**Visual Indicators Feature**:
- Bootstrap badges on each option row showing comparison to intrinsic value
  - Green "✓ Good": Strike ≤ Intrinsic Value (would buy at/below fair value if assigned)
  - Red "✗ High": Strike > Intrinsic Value (would buy above fair value if assigned)
  - Yellow "⚠ N/A": Intrinsic Value not calculated (NULL)
- Badge on accordion header showing overall stock status
  - Green ✓: At least one option has strike ≤ IV
  - Red ✗: All options have strike > IV
  - Yellow ⚠: No intrinsic value calculated
- Uses `preferred_valuation_method` to choose between EPS and FCF intrinsic values
- Template tags for dictionary access and good option detection

**Valuations Page Feature**:
- New page at `/scanner/valuations/` displaying all active curated stocks
- Simple table with columns:
  - Ticker and Company Name
  - Intrinsic Value (EPS) and Intrinsic Value (FCF)
  - Preferred Valuation Method (badge indicator)
  - Last Calculation Date
  - Key Assumptions (growth rates, multiples, desired return)
- Graceful handling of NULL intrinsic values (shows "-" or "Never")
- Authentication required (@login_required)
- Stocks ordered alphabetically by ticker
- Accessible via navbar dropdown menu ("Scanner" → "Stock Valuations")

**Technical Implementation**:
- `CuratedStock.get_effective_intrinsic_value()` model method returns IV based on preferred method
- Scanner views (`scan_view`, `scan_status`) include `curated_stocks` dictionary in context
- Custom template filter `dict_get` for dictionary access in Django templates
- Custom template tag `check_good_options` to determine accordion header badge color
- `valuation_list_view` Django view with queryset filtering and ordering
- Bootstrap 5 badges and table components for styling
- Responsive design with `table-responsive` wrapper for mobile

**Testing**:
- Unit tests for `get_effective_intrinsic_value()` method (6 tests)
- Integration tests for `valuation_list_view` (7 tests)
- Integration tests for scanner view context (4 tests)
- Manual testing checklist covering all scenarios
- Browser compatibility testing (Chrome, Firefox, Safari)
- Responsive design verification (desktop, tablet, mobile)

### Phase 5.2: Testing and Bug Fixes (November 2025)

**Status**: ✅ Completed

**Bugs Fixed**:
- ✅ Scanner index view context bug (Good/Bad pills not displaying)
  - Refactored `index()` view to use DRY helper function
  - Added 3 comprehensive tests with TDD approach
  - Reduced code by 55 lines
  
- ✅ Test suite failures (11 test failures fixed)
  - Fixed URL namespace issues (10 tests)
  - Fixed template include paths (1 test)
  - Added authentication to tests (9 tests)
  - Fixed mock configurations (8 tests)
  - Updated assertions for async behavior (6 tests)
  - Achieved 100% test pass rate: 216/216 tests passing

**Current Status**:
- All Phase 5 objectives completed ✅
- All pending bugs resolved ✅
- All pending refactors completed ✅
- 100% test pass rate (216/216) ✅
- Production-ready with comprehensive error handling ✅
- Ready for Phase 6 ✅

### Phase 6: Stock Price Integration

**Status**: Not started

**Related Tasks**: TBD

**Summary**:
Integrate current stock prices from marketdata API to identify undervalued investment opportunities. Display price comparisons against intrinsic valuations on home page and valuations page.

**Planned Features**:
1. **Stock Price API Integration**
   - Pull current prices from marketdata API (`/v1/stocks/quotes/{symbol}`)
   - Cache prices appropriately (15-min TTL during market hours)
   - Handle market closed scenarios
   - Error handling for API failures

2. **Undervalued Stocks Widget (Home Page)**
   - Display stocks where current price < intrinsic value
   - Show ticker, company name, current price, intrinsic value
   - Calculate undervaluation percentage
   - Sort by best opportunities (highest discount)
   - Refresh daily after market close

3. **Valuations Page Enhancements**
   - Add "Current Price" column
   - Add "% to Intrinsic Value" column
   - Color-code rows (green for undervalued, red for overvalued)
   - Add price update timestamp
   - Filter/sort by undervaluation

4. **Data Management**
   - Cron job to fetch prices daily after market close
   - Store last price and timestamp in database
   - Historical price tracking (optional)

**Technical Considerations**:
- Market hours awareness (9:30 AM - 4:00 PM ET)
- API rate limiting (marketdata.app limits)
- Cache strategy for price data
- Database schema for price storage
- Stale price handling (weekends, holidays)

**Estimated Tasks**: 5-7 tasks

### Phase 7: Create historical storage of valuation calculations

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to store a quarterly calculation of the intrinsic value of each stock.  Ideally I should be able to look back to previous calculations. The storage should start from now and store data for 5 years.  

### Phase 7: Options scanning for individual stocks

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to allow the user to enter an individual stock ticker, select either put or call, and initiate a scan to return options that meet the criteria.  This is similar to the find_options management command and will implement the same functions.  The results should be displayed to the user in a similar manner to the primary scan for options page - this results page does not need to concern itself with the CuratedStock valuations.

### Phase 8: Update the home page with data widgets

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to create a couple of widgets (or data display areas) on the home page for the user.

The initial implementation of this will be with the following data:
- If there are options found and stored in Redis and if the strike price of the options found are below the valuation of the stock (found in CuratedStock), present a widget that shows the ticker name and let's the user know a favorable option was found for these stock tickers.
- Create a list of target stocks for the user using the CuratedStock preferred valuation and the last price of the previous day stock price.
  - Utilize the marketdata api to pull stock price from /v1/stocks/quotes/{symbol}.  Use this data to populate a list of stocks from the CuratedStock list that are currently undervalued.  Display that list on the main index/home page as a widget called Targets.  There will likely need to be a cron job run at the end of the market trading day to capture the last price of the stocks in the CuratedStock list but we can discuss ideas for this data.

### Phase 9: Journal trades

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to create a trading journal similar in concept to the journal I use at https://docs.google.com/spreadsheets/d/1IaMffQtgQxXEf9plX6xhVLi8lfkoKzt1uRNH5SaXqUk/edit?usp=sharing.  Ultimately the purpose of this spreadsheet is to determine income gained from Options sales, stock sales, dividends, and interest.  I want to use this data to see how I am doing on a monthly and yearly basis, capture simple performance, determine how each account is doing, etc.  To do this I need to capture trades I have made on a monthly basis.  Calculate balances for different categories like (Premium for tax advantaged accounts, non-tax advantaged accounts). And there will likely be future enhancements.  This data will be used to calculate taxes owed, and tithes/charitable giving I want to give.