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

### 📈 Campaign Tracking
- **Transaction History**: Track puts, calls, rolls, assignments, and dividends
- **Account Management**: Organize campaigns by account
- **Performance Metrics**: Monitor returns and outcomes per campaign

## Technology Stack

- **Backend**: Django 5.1+, Python 3.13+
- **Database**: PostgreSQL 14.1
- **Cache**: Redis 6.2
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

See `AGENTS.md` for complete command reference.

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
├── tasks/                # Development task files
└── reference/            # Documentation (ROADMAP, BUGS, REFACTORS)
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
- 7-day Redis caching to minimize API calls

## Development Workflow

1. **Review Roadmap**: Check `reference/ROADMAP.md` for current phase
2. **Create Task**: Add numbered task file in `/tasks` directory
3. **Implement**: Follow task specifications
4. **Test**: Run `just test` to verify changes
5. **Document**: Update ROADMAP.md and reference files

See `AGENTS.md` for detailed development guidelines.

## Current Status

**Latest Milestone**: Phase 5 - Visual Indicators & Reliability (Completed ✅)
- Options scanner shows strike price vs. intrinsic value comparison
- Valuations page with highlighted preferred method
- Comprehensive testing and dark mode support
- All critical bugs resolved with defense-in-depth error handling

**Recent Updates**:
- **Nov 10, 2025**: Fixed scanner index view context bug - Good/Bad pills now display correctly
  - Refactored `index()` view to use DRY helper function
  - Ensured consistent context across all scanner views
  - Added 3 comprehensive tests with TDD approach
  - Reduced code complexity by 55 lines
- **Nov 9, 2025**: Scanner reliability improvements
  - Fixed URL routing issue (namespace bug)
  - Added preferred valuation highlighting in UI
  - Implemented LOCAL environment market hours bypass
  - Fixed critical Redis timeout bug with defense-in-depth approach
  - Added 33 tests for error scenarios and graceful degradation

**Next Phase**: Phase 6 - Stock Price Integration
- Pull current prices from market data API
- Display undervalued stocks widget on home page
- Add price column to valuations page
- Calculate and display undervalued opportunities

## Testing

```bash
# Run all tests
just test

# Run specific test file
just test scanner/tests/test_scanner_views.py

# Run with coverage
uv run pytest --cov
```

Total test coverage: 129 tests (74 unit + 55 integration)
- Template filter tests with type safety validation
- Redis error handling and timeout scenarios
- Integration tests for graceful degradation

## Contributing

1. Review `AGENTS.md` for coding standards
2. Follow task-based development workflow
3. Maintain test coverage for new features
4. Update documentation (ROADMAP, task files)

## License

[Your License Here]

## Support

For issues, feature requests, or questions:
- Review `reference/ROADMAP.md` for planned features
- Check `reference/BUGS.md` for known issues
- See `AGENTS.md` for development context

---

**Built with Django + HTMX + Tailwind CSS**
