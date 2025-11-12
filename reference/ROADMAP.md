# Wheel-Analyzer Development Roadmap

Wheel Analyzer is a Django-based web application for tracking and analyzing stock options trading, specifically focused on the "wheel strategy" (selling puts, taking assignment, selling calls). The application helps track options campaigns, individual transactions, and scan for new trading opportunities.

## Overview

Wheel Analyzer looks through a curated list of stocks, finds their options for a given time period and analyzes them, looking for options that provide a 30% or greater annualized return with a delta of less than .20 or -.20

## Development Workflow

1. **Phase Planning**

- Study the existing codebase and understand the current state
- Create a comprehensive specification file in the `/specs` directory
- Name format: `phase-N-description.md` (e.g., `phase-6-historical-valuations.md`)
- Include high-level overview, key features, technical implementation, acceptance criteria, and task breakdown

2. **Phase Implementation**

- Use the `/build` command with the spec file argument: `/build specs/phase-N-description.md`
- Follow the specifications and task breakdown in the spec file
- Implement features and functionality iteratively
- Run tests frequently to verify changes

3. **Roadmap Updates**

- Mark completed phases with ✅ in the roadmap
- Add reference to the spec file (e.g., `See: specs/phase-6-historical-valuations.md`)
- Update current status with key achievements and test counts

## Specification Files

Detailed implementation plans are documented in the `/specs` directory:
- `phase-6-historical-valuations.md` - Historical valuation storage system (8 tasks, 60+ tests)


## Development Phases

### Phase 1: Curated Stock List

**Status**: ✅ Completed

**Summary**:
Successfully migrated from JSON-based stock management to a database-driven CuratedStock model. The scanner commands (`cron_sma` and `cron_scanner`) now query active stocks from the database, enabling dynamic stock management through the Django admin interface. All 26 stocks were successfully imported and verified.

**Key Achievements**:
- Created CuratedStock Django model with admin interface
- Migrated 26 stocks from JSON to database
- Updated scanner commands to use database model

### Phase 2: Manual Scan Trigger

**Status**: ✅ Completed

**Summary**:
Successfully implemented manual scan functionality for the scanner page. Users can now trigger an on-demand options scan by clicking the "Scan for Options" button.

**Key Achievements**:
- Extracted core scanning logic into reusable `perform_scan()` function
- Created Django view with Redis locking mechanism (10-minute timeout)
- Added HTMX-powered button with loading indicator
- Created dedicated partial template for HTMX updates
- Comprehensive error handling with user-friendly messages

### Phase 3: Polling for Scan Progress

**Status**: ✅ Completed

**Summary**:
Successfully implemented a polling mechanism with progressive results display for the manual options scan feature. Users now see real-time feedback as the scan progresses, with options appearing as they're found.

**Key Achievements**:
- Refactored scan view to execute in background threads
- Created polling status endpoint with 15-second intervals
- Built scan polling template with animated status banner
- Progressive results display with real-time updates
- Multi-user support for watching scan progress
- HTMX-powered frontend with seamless state transitions

### Phase 4: Calculate fair value for stocks in the curated list

**Status**: ✅ Completed (Including FCF Enhancement)

**Summary**:
Successfully implemented a valuation system that calculates the intrinsic value (fair value) of stocks using both EPS-based and FCF-based Discounted Cash Flow (DCF) models. The system supports dual valuation methods and respects Alpha Vantage API rate limits through smart stock selection and caching.

**Key Achievements**:
- Added intrinsic value fields to CuratedStock model (EPS and FCF)
- Created DCF calculation engine in `scanner/valuation.py`
- Implemented `calculate_intrinsic_value` management command
- Fetches EPS TTM from Alpha Vantage EARNINGS endpoint
- Fetches FCF data from CASH_FLOW endpoint
- Django cache framework with 7-day TTL for API responses
- 20-second rate limiting (3 calls/minute) for conservative API usage
- Command options: `--symbols`, `--force-refresh`, `--limit`, `--force-all`
- 96 tests passing (56 unit + 40 integration)


### Phase 4.1: API Rate Limit Optimization

**Status**: ✅ Completed

**Summary**:
Successfully optimized the `calculate_intrinsic_value` management command to respect AlphaVantage's free tier limit of 25 API requests per day. Implements a rolling update strategy with smart stock selection.

**Key Achievements**:
- Processes 7 stocks per run (21 API calls, conservative limit) by default
- Prioritizes stocks that have never been calculated (NULL `last_calculation_date`)
- Then processes stocks with oldest calculation dates (stale valuations)
- Added `--limit N` and `--force-all` flags for flexible execution
- Database index on `last_calculation_date` for efficient queries
- API call tracking with cache hit rate reporting
- Enhanced logging with before/after value comparisons and deltas
- Daily rolling updates maintain calculation freshness across portfolio

### Phase 5: Visual Intrinsic Value Indicators

**Status**: ✅ Completed

**Summary**:
Successfully added visual indicators to the options scanner showing whether option strike prices are at or below intrinsic value, and created a comprehensive valuations page for the curated stock list.

**Key Achievements**:
- Color-coded Tailwind CSS badges on scanner showing strike vs. intrinsic value
  - Green "✓ Good": Strike ≤ IV, Red "✗ High": Strike > IV, Yellow "⚠ N/A": No IV
- Accordion header badges showing overall stock status (green/red/yellow)
- New `/scanner/valuations/` page displaying all curated stocks
- Responsive table with EPS/FCF values, preferred method, and assumptions
- `CuratedStock.get_effective_intrinsic_value()` model method
- Custom template filter `dict_get` and tag `check_good_options`
- Fixed Redis timeout bug with defense-in-depth approach
- Comprehensive testing with graceful degradation

### Phase 5.1: Cache Migration to Django Framework

**Status**: ✅ Completed

**Summary**:
Successfully migrated the scanner application from direct Redis usage to Django's cache framework with Redis backend. This migration improves code maintainability, testability, and follows Django best practices.

**Key Achievements**:
- Migrated from direct Redis to Django cache framework
- Automatic serialization and consistent key prefixing
- Alpha Vantage API data: 7-day TTL (604,800 seconds)
- Options scan data: 45-minute TTL (2,700 seconds)
- Added 40+ new cache tests across 7 test files
- 17x performance improvement on cache hits (0.87s → 0.05s)
- Graceful degradation if Redis unavailable
- All cache operations wrapped in try/except blocks
- ~1,500 lines changed across 15 files
- All 216 tests passing (180 scanner + 36 tracker)

### Phase 5.2: Testing and Bug Fixes

**Status**: ✅ Completed

**Summary**:
Achieved 100% test pass rate and resolved all pending bugs and refactors. Production-ready with comprehensive error handling.

**Key Achievements**:
- Fixed scanner index view context bug (Good/Bad pills)
- Refactored `index()` view with DRY helper function
- Fixed 11 test failures (URL namespaces, template paths, authentication, mocks)
- Added 3 comprehensive tests with TDD approach
- Reduced code by 55 lines
- 100% test pass rate: 216/216 tests passing
- All Phase 5 objectives completed
- Ready for Phase 6

### Phase 6: Historical Valuation Storage

**Status**: Planned - Ready for Implementation

**Specification**: `specs/phase-6-historical-valuations.md`

**Summary**:
Create a comprehensive historical valuation storage system that captures quarterly snapshots of intrinsic value calculations with complete DCF assumptions. This enables trend analysis, comparison reports, and tracking valuation changes over time.

**Key Features**:
- ValuationHistory model with quarterly snapshots (Jan 1, Apr 1, Jul 1, Oct 1)
- Stores both EPS and FCF valuation results with complete DCF assumptions
- Quarterly snapshot management command (idempotent, scheduled via cron)
- Per-stock history view at `/scanner/valuations/history/<symbol>/`
- Comparison report view at `/scanner/valuations/comparison/`
- CSV export functionality (single-stock and all-stocks)

**Technical Highlights**:
- PostgreSQL with B-tree indexes for efficient queries
- Storage: ~400 KB for 10 years (50 stocks × 4 quarters × 10 years)
- Testing: 60+ new tests bringing total to 276 tests
- Query performance: <200ms for stock history, <300ms for comparison report
- Backwards compatible with existing CuratedStock model

**Estimated Effort**: 8-12 hours across 8 tasks

See `specs/phase-6-historical-valuations.md` for complete specifications and task breakdown.

### Phase 6.1: Visualizations and Advanced Analytics

**Status**: To be planned later

**Summary**:
Enhance Phase 6 historical valuation features with interactive visualizations, advanced analytics, and API integration.

**Planned Features**:
- Chart.js visualizations (line charts, bar charts, stacked area charts)
- Advanced analytics (volatility, sensitivity, CAGR, correlation)
- REST API endpoints with Django REST Framework
- Historical price tracking (integrates with Phase 8)
- Notification system (email alerts, weekly digests)

**Technical Highlights**:
- Chart.js for client-side rendering
- Analytics module: `scanner/analytics.py`
- Celery + Redis for async notifications
- Django signals for event-driven architecture

**Dependencies**: Requires Phase 6 completion, integrates with Phase 8

**Estimated Effort**: 10-15 hours across 5-7 tasks

### Phase 7: Individual Stock Options Scanning

**Status**: Not started

**Summary**:
Allow users to enter an individual stock ticker, select option type (put or call), and initiate a scan to return options that meet the criteria. Similar to the `find_options` management command functionality.

**Key Features**:
- User input form for ticker symbol and option type selection
- On-demand scanning for individual stocks (not limited to curated list)
- Results display similar to primary scanner page
- No intrinsic value comparison required (optional enhancement)

### Phase 8: Stock Price Integration

**Status**: Not started

**Summary**:
Integrate current stock prices from marketdata API to identify undervalued investment opportunities. Display price comparisons against intrinsic valuations.

**Planned Features**:
- Stock price API integration (marketdata API `/v1/stocks/quotes/{symbol}`)
- Undervalued stocks widget on home page
- Valuations page enhancements (current price column, undervaluation %)
- Daily cron job to fetch prices after market close
- Database storage for prices and timestamps

**Technical Considerations**:
- Market hours awareness (9:30 AM - 4:00 PM ET)
- Cache strategy (15-min TTL during market hours)
- API rate limiting (marketdata.app limits)
- Stale price handling (weekends, holidays)

**Estimated Effort**: 5-7 tasks

### Phase 9: Home Page Widgets

**Status**: Not started

**Summary**:
Create data widgets on the home page to highlight actionable opportunities for the user.

**Planned Features**:
- **Favorable Options Widget**: Display stocks with options found where strike price ≤ intrinsic value
- **Target Stocks Widget**: List of undervalued stocks (current price < preferred intrinsic value)
- Pull current prices from marketdata API
- Daily cron job to update data after market close
- Clear, actionable display with tickers and key metrics

### Phase 10: Trading Journal

**Status**: Not started

**Summary**:
Create a comprehensive trading journal to track income from options sales, stock sales, dividends, and interest for performance tracking and tax planning.

**Planned Features**:
- Monthly trade entry and tracking
- Income categorization (options premium, stock sales, dividends, interest)
- Account-based tracking (tax-advantaged vs. non-tax-advantaged)
- Monthly and yearly performance summaries
- Balance calculations by category
- Tax calculation support
- Tithes/charitable giving calculations

**Future Enhancements**:
- Performance metrics and visualizations
- Import from brokerage statements
- Export for tax filing