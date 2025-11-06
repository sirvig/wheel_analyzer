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
   - 15-second rate limiting (4 calls/minute) for API call limits
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

# Schedule weekly (Monday 8 PM)
0 20 * * 1 cd /path/to/project && python manage.py calculate_intrinsic_value
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
- Rate limiting: 15 seconds (4 calls/minute) for Alpha Vantage API limits
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

### Phase 5: Update Option Scanner to provide a visual representation of intrinsic value

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to present the user with a visual representation that the option strike price is at or below the intrinsic value calculated above.
When the Scan for options job is run and options are found to be displayed - if the option strike price is at or below the intrinsic value that was last calculated there should be a green light added.  If its above the intrinsic value, a red light should be added.  If any of the options found for a stock are at or below the intrinsic value, a green light should be added to the accordian tab as well.  Otherwise a red light should be added.

Additionally, we need a single page view of the curated list and their valuations.

### Phase 6: Create historical storage of valuation calculations

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to store a quarterly calculation of the intrinsic value of each stock.  Ideally I should be able to look back to previous calculations. The storage should start from now and store data for 5 years.  