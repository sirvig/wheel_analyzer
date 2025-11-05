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

**Status**: In Progress

**Related Tasks**:

- ⏳ `013-add-intrinsic-value-fields.md` - Add database fields to CuratedStock model for intrinsic value and DCF assumptions
- ⏳ `014-dcf-calculation-functions.md` - Create DCF calculation utility functions (EPS-based)
- ⏳ `015-valuation-management-command.md` - Create weekly management command to calculate intrinsic values
- ⏳ `016-valuation-testing.md` - Add comprehensive unit and integration tests

**Summary**:
Implement a weekly valuation system that calculates the intrinsic value (fair value) of stocks in the curated list using an EPS-based Discounted Cash Flow (DCF) model. The system will:

**EPS-based DCF Process** (Initial Implementation):
1. **Project EPS**: Calculate projected EPS for 5 years using configurable growth rate
2. **Terminal Value**: Calculate terminal value as Final Year EPS × EPS Multiple
3. **Present Value of Projected EPS**: Discount each year's projected EPS to present value using desired return rate
4. **Present Value of Terminal Value**: Discount terminal value to present value
5. **Intrinsic Value**: Sum all present values to determine fair value per share

**Implementation Details**:
- **Database Fields**: Add to CuratedStock model:
  - Calculation results: `intrinsic_value`, `last_calculation_date`
  - DCF assumptions: `current_eps`, `eps_growth_rate` (default: 10%), `eps_multiple` (default: 20), `desired_return` (default: 15%), `projection_years` (default: 5)
- **Data Source**: Fetch current EPS from Alpha Vantage OVERVIEW endpoint
- **Assumptions**: Manually configurable per stock via Django admin
- **Caching**: Redis cache for API responses (7-day TTL)
- **Rate Limiting**: 12-second delays between API calls (5 calls/minute limit)
- **Execution**: Django management command (`calculate_intrinsic_value`) scheduled for Monday evenings
- **Error Handling**: Skip stocks with missing/invalid data, log errors, continue processing

**DCF Formula**:
```
Projected EPS[year] = Current EPS × (1 + growth_rate)^year
Terminal Value = Projected EPS[Year 5] × EPS Multiple
PV of EPS[year] = Projected EPS[year] / (1 + desired_return)^year
PV of Terminal = Terminal Value / (1 + desired_return)^5
Intrinsic Value = Sum(PV of all Projected EPS) + PV of Terminal Value
```

**FCF-based DCF** (Future Enhancement):
Deferred to future phase. Will require research on data sources for Free Cash Flow per share.

**Testing**:
- Unit tests for DCF calculation accuracy
- Integration tests with mocked API responses
- Performance tests to ensure scalability
- Optional live API tests for validation

See task files for detailed implementation specifications.

### Phase 5: Update Option Scanner to provide a visual representation of intrinsic value

**Status**: Not started

**Related Tasks**:

**Summary**:
The goal here is to present the user with a visual representation that the option strike price is at or below the intrinsic value calculated above.
When the Scan for options job is run and options are found to be displayed - if the option strike price is at or below the intrinsic value that was last calculated there should be a green light added.  If its above the intrinsic value, a red light should be added.  If any of the options found for a stock are at or below the intrinsic value, a green light should be added to the accordian tab as well.  Otherwise a red light should be added.
