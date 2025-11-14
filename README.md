# Wheel Analyzer

A Django-based web application for tracking and analyzing stock options trading using the "wheel strategy" (selling puts, taking assignment, selling calls).

## Features

### 📊 Options Scanner
- **Manual Scan Trigger**: Click to scan for options opportunities in real-time
- **Progressive Results**: Watch results appear as each stock is scanned
- **Market Hours Awareness**: Automatically restricts scans to trading hours (9:30 AM - 4:00 PM ET)
- **Development Mode**: Local environment bypass for testing outside market hours
- **Visual Indicators**: Color-coded badges showing strike price vs. intrinsic value comparison

### 🔍 Individual Stock Scanner
- **Custom Ticker Search**: Search for options on any stock ticker (not just curated list)
- **Option Type Selection**: Choose between put or call options with radio button interface
- **Background Scanning**: User-isolated scans with real-time progress updates via HTMX polling
- **Intrinsic Value Badges**: Conditional display for curated stocks (✓ Good, ✗ High, ⚠ N/A)
- **Multi-User Support**: Isolated cache keys per user ID prevent cross-user interference
- **Flexible Time Range**: Specify weeks parameter (1-52 range, default: 4 weeks)

### 💾 Saved Searches
- **Bookmark Tickers**: Save frequently scanned tickers for quick access
- **One-Click Scanning**: Trigger scans directly from saved searches list
- **Notes & Organization**: Add notes for categorization and context
- **Usage Tracking**: Automatic scan counter and last scanned timestamp
- **Flexible Sorting**: Sort by date created, ticker name, scan frequency, or last scanned
- **Inline Editing**: Update notes via HTMX without page reloads
- **Soft Delete Pattern**: Preserves audit trail and scan history

### 📊 API Usage Dashboard
- **Daily Quota Tracking**: Monitor individual search scan usage (25 scans/day default)
- **Visual Progress**: Color-coded progress bars showing quota consumption
- **7-Day History**: Chart.js visualization of daily scan patterns
- **Reset Countdown**: Timer showing time until midnight quota reset (US/Eastern)
- **Breakdown by Type**: Separate counters for curated vs. individual scans
- **Quota Exceeded Handling**: Friendly error messages with reset time

### 🛠️ Staff Monitoring (Admin Only)
- **Scan Status Tracking**: Real-time database tracking of all background scan operations
- **Redis Lock Monitoring**: Visual indicators for lock state with TTL display
- **Clear Lock Button**: One-click resolution for stuck scans with database updates
- **Auto-Refresh**: Dashboard updates every 10 seconds automatically
- **Comprehensive Logging**: Audit trail for all admin actions and scan lifecycle events
- **Django Admin Integration**: Full CRUD interface with filters, search, and date hierarchy

### 💰 Valuation System
- **Dual DCF Models**: Calculate intrinsic value using both EPS and FCF methods
- **Smart Stock Selection**: Prioritize never-calculated and oldest stocks to respect API limits
- **Preferred Method**: Choose between EPS or FCF valuation per stock
- **Visual Highlighting**: At-a-glance identification of preferred valuation method
- **Daily Rolling Updates**: Automated calculations with 7-stock daily limit
- **Historical Snapshots**: Quarterly valuation history with complete DCF assumptions

### 📉 Analytics & Visualization
- **Interactive Charts**: Chart.js visualizations on analytics, history, and comparison pages
- **Trend Analysis**: Multi-line charts showing intrinsic value changes over time
- **Portfolio Metrics**: Aggregate statistics including average IV, volatility, and CAGR
- **Quick Stats**: Highest, lowest, and average intrinsic values with date tracking
- **Method Comparison**: Visual comparison of EPS vs. FCF valuation methods
- **Performance Analytics**: Volatility, correlation, and compound annual growth rate calculations

### 📈 Campaign Tracking
- **Transaction History**: Track puts, calls, rolls, assignments, and dividends
- **Account Management**: Organize campaigns by account
- **Performance Metrics**: Monitor returns and outcomes per campaign

## Technology Stack

- **Backend**: Django 5.1+, Python 3.13+
- **Database**: PostgreSQL 14.1
- **Cache**: Redis 6.2 with Django cache framework
- **Frontend**: HTMX, Tailwind CSS, Flowbite
- **Package Manager**: uv
- **Task Runner**: just
- **Deployment**: Docker

## Quick Start

### Prerequisites
- Python 3.13+
- PostgreSQL 14.1+
- Redis 6.2+
- Docker (optional, for containerized services)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wheel-analyzer
   ```

2. **Copy environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start services** (PostgreSQL and Redis)
   ```bash
   just up
   ```

4. **Run migrations**
   ```bash
   just exec python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   just exec python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   just run
   ```

Visit `http://localhost:8000` to access the application.

## Environment Configuration

The application uses an `ENVIRONMENT` variable to control behavior:

- **`LOCAL`**: Development environment
  - Allows options scanning outside market hours
  - Shows development mode warnings
  - Ideal for testing and debugging

- **`TESTING`**: Test environment
  - Automatically set by pytest
  - Uses test database

- **`PRODUCTION`**: Production environment (default)
  - Enforces market hours restrictions
  - Production-ready configuration

Set in your `.env` file:
```bash
ENVIRONMENT=LOCAL  # or TESTING, PRODUCTION
```

## Key Commands

### Development
- `just test` - Run test suite
- `just lint` - Format and check code
- `just run` - Start Django dev server
- `just up` - Start Docker services
- `just kill` - Stop Docker services

### Management Commands
- `python manage.py calculate_intrinsic_value` - Calculate DCF valuations
- `python manage.py cron_scanner` - Scheduled options scan
- `python manage.py cron_sma` - Calculate moving averages

See `CLAUDE.md` for complete command reference.

## Project Structure

```
wheel-analyzer/
├── scanner/              # Options scanning and valuation
│   ├── marketdata/       # Market data API integration
│   ├── alphavantage/     # Alpha Vantage API integration
│   ├── valuation.py      # DCF calculation engine
│   ├── analytics.py      # Volatility, CAGR, correlation calculations
│   ├── quota.py          # API usage tracking and enforcement
│   ├── forms.py          # IndividualStockScanForm
│   └── models.py         # CuratedStock, ValuationHistory, SavedSearch, ScanStatus, ScanUsage, UserQuota
├── tracker/              # Campaign and transaction tracking
│   └── models.py         # User, Account, Campaign, Transaction
├── templates/            # Django templates
├── static/               # CSS, JS, images
├── specs/                # Phase implementation specifications
└── reference/            # Documentation (ROADMAP)
```

## API Integrations

### Market Data API
- Real-time options chains
- Strike prices, deltas, implied volatility
- Used for options scanning

### Alpha Vantage API
- Quarterly earnings (EPS TTM)
- Cash flow statements (FCF TTM)
- Company fundamentals
- 7-day Django cache to minimize API calls

## Development Workflow

1. **Review Roadmap**: Check `reference/ROADMAP.md` for current phase
2. **Create Specification**: Add comprehensive spec file in `/specs` directory (format: `phase-N-description.md`)
3. **Implement**: Use `/build specs/phase-N-description.md` to start implementation
4. **Test**: Run `just test` frequently to verify changes
5. **Document**: Update ROADMAP.md with completion status and key achievements

See `CLAUDE.md` for detailed development guidelines and `specs/` directory for phase specifications.

## Current Status

**Latest Milestone**: Phase 7.2 - Rate Limit Dashboard + Staff Monitoring (Completed ✅)
- **Phase 7.2**: API usage tracking with daily quota enforcement (25 scans/day)
  - ScanUsage and UserQuota models with atomic check-and-record
  - Usage dashboard with 7-day Chart.js history and progress bars
  - Quota exceeded handling with HTTP 429 responses and friendly error messages
  - Midnight resets with US/Eastern timezone handling
  - 433 tests passing (100% pass rate)
- **Staff Monitoring** (Ad-hoc): Diagnostic page for background scan operations
  - ScanStatus model tracking all scan operations with status and timestamps
  - Staff-only page at `/scanner/admin/monitor/` with auto-refresh (10s)
  - Redis lock monitoring with TTL display and one-click clear button
  - Django admin integration with full CRUD, filters, and date hierarchy
  - 472 tests passing (100% pass rate) - 21 new comprehensive tests

**Recent Updates**:
- **Nov 14, 2025**: Staff Monitoring Implementation Complete (Ad-hoc)
  - ScanStatus model with status transitions and duration calculations
  - Staff-only monitoring page with Redis lock diagnostics
  - Clear lock button that deletes lock AND marks active scans as aborted
  - Auto-refresh dashboard with formatted duration display
  - Django admin integration with custom duration formatting
  - 11 files changed, ~935 lines added
  - 21 new tests (100% pass rate) - model, view, and integration coverage

- **Nov 14, 2025**: Phase 7.2 Implementation Complete (Rate Limit Dashboard)
  - ScanUsage model tracking every individual search scan
  - UserQuota model with per-user daily limits (default 25/day)
  - Atomic quota enforcement with row locking prevents concurrent bypass
  - Usage dashboard with Chart.js 7-day history and countdown timers
  - HTTP 429 responses with quota exceeded partial template
  - Midnight resets with US/Eastern timezone handling
  - 14 new tests (100% pass rate) - quota enforcement and dashboard tests
- **Nov 13, 2025**: Phase 7.1 Implementation Complete (Save Searches)
  - SavedSearch model with 8 fields and soft delete pattern
  - Custom manager with `active()` and `for_user()` helper methods
  - 5 new views: list with sorting, save, delete, quick scan, edit notes
  - 4 new templates with HTMX integration (250+ lines)
  - User isolation: ForeignKey with CASCADE, unique constraint on (user, ticker, option_type)
  - Usage tracking: automatic scan counter and last_scanned_at timestamp
  - 11 files changed, 560 lines added
  - Security audit: XSS vulnerability fixed with |escapejs filter
  - 340 tests passing (100% pass rate) - 79 comprehensive tests generated

- **Nov 13, 2025**: Phase 7 Implementation Complete (Individual Stock Scanner)
  - IndividualStockScanForm with ticker validation and normalization
  - Background scan with user-specific cache keys (10-minute TTL)
  - 4 new views: search form, scan trigger, status polling, context helper
  - 3 new templates with HTMX polling (5-second intervals)
  - Conditional intrinsic value badges for curated stocks
  - Multi-user support with isolated cache keys per user ID
  - 7 files changed, 495 lines added
  - 302 tests passing (100% pass rate) - 37 new tests generated

- **Nov 12, 2025**: Phase 6.1 Implementation Complete (Analytics & Visualizations)
  - Created `scanner/analytics.py` module (546 lines) with 6 analytics functions
  - Built dedicated analytics page at `/scanner/valuations/analytics/`
  - Added embedded charts to history and comparison pages (Chart.js 4.4.1)
  - Portfolio analytics: average IV, volatility, CAGR across all stocks
  - Stock analytics: volatility (std dev, CV), CAGR, EPS/FCF correlation
  - Dark mode support with computed CSS variables

- **Nov 12, 2025**: Phase 6 Implementation Complete (Historical Valuations)
  - ValuationHistory model with quarterly snapshots
  - Management command: `create_quarterly_valuation_snapshot`
  - Per-stock history view with chronological table
  - Comparison report view with side-by-side analysis
  - CSV export functionality (single stock and all stocks)
  - 31 new tests bringing total to 247 tests

**Next Phase**: Phase 8 - Stock Price Integration
- Integrate current stock prices from marketdata API
- Identify undervalued investment opportunities (price < intrinsic value)
- Undervalued stocks widget on home page
- Valuations page enhancements with current price column
- Daily cron job to fetch prices after market close
- Full specification available in `reference/ROADMAP.md`

## Testing

```bash
# Run all tests
just test

# Run specific test file
just test scanner/tests/test_scanner_views.py

# Run with coverage
uv run pytest --cov
```

**Test Suite**: 472 tests passing (100% pass rate) ✅
- Scanner views and integration tests (curated + individual)
- Valuation calculation tests (EPS & FCF methods)
- Template filter tests with type safety validation
- Redis error handling and timeout scenarios
- Integration tests for graceful degradation
- Authentication and authorization tests
- Cache framework tests (Django cache with Redis backend)
- Analytics and visualization tests (Phase 6.1)
- Individual stock scanning tests (Phase 7 - 37 tests)
- Saved searches tests (Phase 7.1 - 79 tests)
- Quota enforcement tests (Phase 7.2 - 14 tests)
- Staff monitoring tests (Ad-hoc - 21 tests)

## Roadmap

### Completed Phases
- ✅ **Phase 1**: Curated Stock List (database-driven)
- ✅ **Phase 2**: Manual Scan Trigger (HTMX-powered)
- ✅ **Phase 3**: Polling for Scan Progress (real-time updates)
- ✅ **Phase 4**: Fair Value Calculations (EPS & FCF DCF models)
- ✅ **Phase 4.1**: API Rate Limit Optimization (rolling updates)
- ✅ **Phase 5**: Visual Intrinsic Value Indicators (color-coded badges)
- ✅ **Phase 5.1**: Cache Migration to Django Framework (17x faster)
- ✅ **Phase 5.2**: Testing and Bug Fixes (100% test pass rate)
- ✅ **Phase 6**: Historical Valuation Storage (quarterly snapshots, CSV export)
- ✅ **Phase 6.1**: Visualizations & Analytics (Chart.js, volatility, CAGR, correlation)
- ✅ **Phase 7**: Individual Stock Scanning (custom ticker search, HTMX polling)
- ✅ **Phase 7.1**: Save Searches (bookmark tickers, one-click scans, soft delete)
- ✅ **Phase 7.2**: Rate Limit Dashboard (API quota tracking, usage visualization, 433 tests)
- ✅ **Ad-hoc**: Staff Monitoring (scan diagnostics, Redis lock management, 472 tests)

### Planned Phases
- 📋 **Phase 8**: Stock Price Integration (marketdata API, undervaluation analysis)
- 📋 **Phase 9**: Home Page Widgets (undervalued stocks, favorable options)
- 📋 **Phase 10**: Trading Journal (performance tracking, tax calculations)

See `reference/ROADMAP.md` for detailed phase descriptions.

## Contributing

1. Review `CLAUDE.md` for coding standards
2. Follow spec-based development workflow (see `specs/` directory)
3. Maintain test coverage for new features (>90% target)
4. Update documentation (ROADMAP, spec files)

## License

Private project - All rights reserved

## Support

For issues, feature requests, or questions:
- Review `reference/ROADMAP.md` for planned features
- See `CLAUDE.md` for development context
- Check `specs/` directory for phase implementation specifications

---

**Built with Django + HTMX + Tailwind CSS**
