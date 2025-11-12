# Wheel Analyzer

A Django-based web application for tracking and analyzing stock options trading using the "wheel strategy" (selling puts, taking assignment, selling calls).

## Features

### 📊 Options Scanner
- **Manual Scan Trigger**: Click to scan for options opportunities in real-time
- **Progressive Results**: Watch results appear as each stock is scanned
- **Market Hours Awareness**: Automatically restricts scans to trading hours (9:30 AM - 4:00 PM ET)
- **Development Mode**: Local environment bypass for testing outside market hours
- **Visual Indicators**: Color-coded badges showing strike price vs. intrinsic value comparison

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
│   └── models.py         # CuratedStock, OptionsWatch models
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

**Latest Milestone**: Phase 6.1 - Analytics & Visualizations (Completed ✅)
- Interactive Chart.js visualizations on 3 pages (analytics, history, comparison)
- Comprehensive analytics module with volatility, CAGR, and correlation calculations
- Portfolio-wide metrics dashboard with trend charts
- Per-stock quick stats and analytics cards
- Method comparison bar charts and dual-line trend charts
- Dark mode support across all visualizations
- **Core features implemented** - Sensitivity analysis deferred to future phase

**Recent Updates**:
- **Nov 12, 2025 (Afternoon)**: Phase 6.1 Implementation Complete
  - Created `scanner/analytics.py` module (546 lines) with 6 analytics functions
  - Built dedicated analytics page at `/scanner/valuations/analytics/`
  - Added embedded line chart to stock history page with quick stats boxes
  - Added embedded bar chart to comparison report page
  - Integrated Chart.js 4.4.1 for client-side interactive visualizations
  - All charts support dark mode with computed CSS variables
  - Portfolio analytics: average IV, volatility, CAGR across all stocks
  - Stock analytics: volatility (std dev, CV), CAGR, EPS/FCF correlation
  - Code quality: All linting checks passed

- **Nov 12, 2025 (Morning)**: Workflow Restructuring
  - Migrated from individual task files to comprehensive spec files
  - Updated development workflow to use `/build` command with spec file arguments
  - Simplified ROADMAP.md to reference spec files instead of individual tasks
  - All documentation updated to reflect new spec-based workflow

- **Nov 11, 2025**: Phase 6 Planning Complete
  - Created comprehensive implementation plan (`specs/phase-6-historical-valuations.md`)
  - Updated ROADMAP.md with Phase 6 and Phase 6.1 sections
  - Ready for implementation: Quarterly snapshots, per-stock history, comparison reports, CSV export
  - Estimated implementation: 8-12 hours across 8 tasks
  - Target: 276/276 tests (60 new tests planned)

- **Nov 10, 2025 (Evening)**: Completed cache migration to Django framework
  - Migrated from direct Redis usage to Django cache backend
  - Added 40+ new cache tests for comprehensive coverage
  - Achieved 17x performance improvement on cache hits
  - Alpha Vantage API caching: 7-day TTL (604,800s)
  - Scanner options caching: 45-min TTL (2,700s)
  - All 216 tests passing with improved testability

- **Nov 10, 2025 (PM)**: Fixed all failing tests - achieved 100% test pass rate
  - Fixed URL namespace issues (10 tests)
  - Fixed template include paths (1 test)
  - Added authentication to tests (9 tests)
  - Fixed mock configurations (8 tests)
  - Updated assertions for async behavior (6 tests)

- **Nov 10, 2025 (AM)**: Fixed scanner index view context bug
  - Refactored `index()` view to use DRY helper function
  - Ensured consistent context across all scanner views
  - Added 3 comprehensive tests with TDD approach

**Next Phase**: Phase 6 - Historical Valuation Storage
- Store quarterly snapshots of intrinsic value calculations (Jan 1, Apr 1, Jul 1, Oct 1)
- Per-stock history pages with trend analysis
- Comparison reports (current vs. previous quarter vs. year-ago)
- CSV export for external analysis (Excel, Google Sheets, Python)
- Track complete DCF assumptions with each snapshot
- Full specification available in `specs/phase-6-historical-valuations.md`

## Testing

```bash
# Run all tests
just test

# Run specific test file
just test scanner/tests/test_scanner_views.py

# Run with coverage
uv run pytest --cov
```

**Test Suite**: 216 tests passing (100% pass rate) ✅
- Scanner views and integration tests
- Valuation calculation tests (EPS & FCF methods)
- Template filter tests with type safety validation
- Redis error handling and timeout scenarios
- Integration tests for graceful degradation
- Authentication and authorization tests
- Cache framework tests (Django cache with Redis backend)

**Phase 6 Target**: 276 tests (216 existing + 60 new)

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

### Planned Phases
- 📋 **Phase 6**: Historical Valuation Storage - **Ready for implementation** (See `specs/phase-6-historical-valuations.md`)
- 📋 **Phase 6.1**: Visualizations & Analytics (Chart.js, advanced analytics, API)
- 📋 **Phase 7**: Individual Stock Scanning (custom ticker search)
- 📋 **Phase 8**: Stock Price Integration (marketdata API)
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
