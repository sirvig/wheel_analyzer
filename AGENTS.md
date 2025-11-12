# AGENTS.md

This file provides guidance to opencode when working with code in this repository.

## Project Overview

Wheel Analyzer is a Django-based web application for tracking and analyzing stock options trading, specifically focused on the "wheel strategy" (selling puts, taking assignment, selling calls). The application helps track options campaigns, individual transactions, and scan for new trading opportunities.

## Technology Stack

- **Backend**: Django 5.1+, Python 3.13+
- **Database**: PostgreSQL 14.1
- **Cache/Queue**: Redis 6.2
- **Frontend**: HTMX for dynamic updates, vanilla JavaScript
- **Package Management**: uv (fast Python package installer)
- **Task Runner**: just (Makefile alternative in Rust)
- **Deployment**: Docker with docker-compose
- **Linting/Formatting**: ruff

## Development Commands

This project uses `just` as the task runner. All commands below should be run with `just <command>`.

### Essential Commands

- `just test` - Run pytest test suite (requires PostgreSQL on port 65432)
- `just test <path>` - Run specific test file or directory
- `just lint` - Format and check code with ruff
- `just run` or `just runserver` - Start Django development server (local, not Docker)
- `just up` - Start Docker services (PostgreSQL and Redis)
- `just kill` - Stop Docker services
- `just dbconsole` - Open PostgreSQL console

### Django Management Commands

Use `just exec python manage.py <command>` for Docker environment, or `uv run manage.py <command>` for local development.

#### Standard Django Commands
- `just exec python manage.py makemigrations` - Generate migrations from model changes
- `just exec python manage.py migrate` - Apply database migrations
- `just exec python manage.py createsuperuser` - Create admin user

#### Custom Management Commands
- `just options <args>` - Run `find_options` command to scan for options opportunities
- `just roll <args>` - Run `find_rolls` command to find roll opportunities
- `just scan <args>` - Run `cron_scanner` to scan and cache options data
- `just sma <args>` - Run `cron_sma` to calculate simple moving averages
- `just premium <args>` - Run `calculate_minimum_premium` command
- `python manage.py calculate_intrinsic_value` - Calculate DCF intrinsic values for curated stocks (EPS & FCF methods)

### Database Operations

- `just backup` - Backup database to `/backups/` in container
- `just mount-docker-backup` - Copy all backups to local machine
- `just mount-docker-backup <filename>` - Copy specific backup file
- `just restore <backup-file>` - Restore database from backup file

### Redis Operations

- `just redis-cli <args>` - Access Redis CLI (password: myStrongPassword, port: 36379)

### Docker Operations

- `just build` - Build Docker image for deployment
- `just docker-run` - Run built Docker image locally
- `just docker-stop` - Stop running Docker container

## Architecture

**Development Context:**
- See @reference/ROADMAP.md for current status and next steps
- Spec-based development workflow with comprehensive specifications in the `/specs` directory
- Use `/build specs/phase-N-description.md` to start implementation of a new phase

### Django Apps

**tracker**: Core application for tracking options trading campaigns and transactions
- Models: `User` (custom auth user), `Account`, `Campaign`, `Transaction`
- Tracks complete trading history per campaign (stock + account combination)
- Transaction types: put, call, roll, buy, sell, btc (buy to close), div (dividend)
- Custom QuerySets via managers: `CampaignsQuerySet`, `TransactionsQuerySet`

**scanner**: Options scanning and analysis tools
- Models: `OptionsWatch` - watchlist for stocks to monitor, `CuratedStock` - stocks for valuation analysis
- External integrations:
  - `scanner/marketdata/` - Market data API wrapper for fetching options chains
  - `scanner/alphavantage/` - Alpha Vantage API integration for fundamental data (EPS, FCF) and technical analysis (SMA calculations)
- Custom management commands for scanning and analyzing options data
- Valuation module (`scanner/valuation.py`) - DCF calculations using EPS and FCF methods
- Caches options data and Alpha Vantage API responses in Redis for performance

### Key Files

- `wheel_analyzer/settings.py` - Django settings, uses `django-environ` for configuration
- `pyproject.toml` - Python dependencies managed by uv
- `justfile` - Task runner definitions
- `docker-compose.yml` - Local development services (PostgreSQL, Redis)
- `Dockerfile` - Production container build

### External Services

- **PostgreSQL**: Port 65432 (local dev), credentials from `.env`
- **Redis**: Port 36379, password: "myStrongPassword"
- Database connection via `DATABASE_URL` environment variable (parsed by `dj-database-url`)

### Authentication

- Custom user model: `tracker.User` (extends `AbstractUser`)
- Uses `django-allauth` for authentication flows
- Login redirect: `index` (home page)

### Static Files

- Managed by `whitenoise` for efficient serving
- Static files in `static/`, templates in `templates/`
- Compressed manifest storage in production

### Testing

- Uses `pytest-django` for testing framework
- All tests are integration tests requiring database connection
- Test database: PostgreSQL on localhost:65432
- Test environment set via `ENVIRONMENT=TESTING` in pytest config
- Run tests with `just test` (or `uv run pytest` directly)

### Logging

- JSON formatted logs via custom `wheel_analyzer.logs.JSONFormatter`
- Django errors logged at ERROR level
- Application logs at INFO level
- All logs output to stdout

### Caching

**Strategy**: Django cache framework with Redis backend

**Configuration**:
- Backend: `django.core.cache.backends.redis.RedisCache`
- Connection: Uses `REDIS_URL` from environment variables (default: `redis://localhost:36379/1`)
- Cache prefix: `wheel_analyzer` namespace (automatically managed by Django)
- Settings: See `wheel_analyzer/settings.py` for CACHES configuration

**Cache Types & TTLs**:
- **Alpha Vantage API data**: 7-day TTL (604,800 seconds)
  - Cache keys: `alphavantage:earnings:{symbol}`, `alphavantage:cashflow:{symbol}`, `alphavantage:overview:{symbol}`, `alphavantage:time_series_daily:{symbol}:period={days}`
  - Purpose: Reduces API consumption (Alpha Vantage limit: 25 calls/day)
  - Set via: `settings.CACHE_TTL_ALPHAVANTAGE`
  
- **Options scan data**: 45-minute TTL (2,700 seconds)
  - Cache keys: `scanner:ticker_options`, `scanner:last_run`, `scanner:scan_in_progress`
  - Purpose: Balances market data freshness with performance
  - Set via: `settings.CACHE_TTL_OPTIONS`

**Usage Pattern**:
```python
from django.core.cache import cache
from django.conf import settings

# Set with TTL
cache.set(f"alphavantage:earnings:{symbol}", data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)

# Get with default
data = cache.get(f"alphavantage:earnings:{symbol}", default={})

# Delete specific key
cache.delete(f"alphavantage:earnings:{symbol}")

# Clear all cache (use sparingly)
cache.clear()
```

**Error Handling**:
- All cache operations wrapped in try/except blocks
- Graceful degradation if Redis unavailable (app continues working)
- Cache failures logged at WARNING level
- Views return safe defaults (empty dicts) on cache errors

**Testing**:
- Tests use `@patch("django.core.cache.cache")` to mock cache
- No real Redis required for running tests
- Cache integration verified through dedicated test files:
  - `scanner/tests/test_django_cache.py` - Cache backend tests
  - `scanner/tests/test_alphavantage_cache.py` - Alpha Vantage caching
  - `scanner/tests/test_redis_integration.py` - Redis error handling

**Manual Cache Operations**:
```bash
# Clear all cache via Django shell
uv run python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# View cache keys via Redis CLI
just redis-cli KEYS "*"
just redis-cli KEYS "*alphavantage*"
just redis-cli KEYS "*scanner*"

# Check TTL on specific key
just redis-cli TTL "wheel_analyzer:1:alphavantage:earnings:AAPL"

# Delete specific key
just redis-cli DEL "wheel_analyzer:1:scanner:ticker_options"
```

## Development Workflow

### Initial Setup

1. Ensure `.env` file exists (copy from `.env.example` if needed)
2. Create Docker network: `docker network create app_main`
3. Start services: `just up`
4. Run migrations: `just exec python manage.py migrate`
5. Create superuser: `just exec python manage.py createsuperuser`

### Local Development (without Docker for app)

The Django application can run locally while using Docker only for PostgreSQL and Redis:

1. Start services: `just up`
2. Run development server: `just run`
3. Run tests: `just test`

### Migration Workflow

1. Modify models in `tracker/models.py` or `scanner/models.py`
2. Generate migrations: `just exec python manage.py makemigrations`
3. Review generated migration files
4. Apply migrations: `just exec python manage.py migrate`
5. To downgrade: `just exec python manage.py showmigrations` then `just exec python manage.py migrate <app> <migration_number>`

## Code Conventions

- Custom QuerySets defined in `managers.py` files within each app
- Factories for testing in `factories.py` (using factory_boy)
- Forms in `forms.py` files
- Filters in `filters.py` (using django-filter)
- Template tags in `templatetags/` directories
- Tests in `tests/` directories within apps
- Timezone: US/Eastern

**Development Context:**
- See @reference/ROADMAP.md for current status and next steps
- Spec-based development workflow with comprehensive specifications in `/specs` directory
- Use `/build specs/phase-N-description.md` to start implementation of a new phase
- **Current Status**: Phase 6 completed ✅ - Historical Valuation Storage system fully implemented with 247/247 tests passing (100% pass rate). Production-ready with comprehensive tracking of quarterly intrinsic value snapshots. Key achievements:
  - ValuationHistory model with quarterly snapshots (Jan 1, Apr 1, Jul 1, Oct 1)
  - Management command: `create_quarterly_valuation_snapshot` with --date, --symbols, --force, --dry-run flags
  - Per-stock history view at `/scanner/valuations/history/<symbol>/` with chronological snapshots table
  - Comparison report at `/scanner/valuations/comparison/` with color-coded deltas (current vs. quarter vs. year)
  - CSV export: `/scanner/valuations/export/` (all stocks) and `/scanner/valuations/export/<symbol>/` (single stock)
  - Updated valuations page with "Comparison Report", "Export All CSV", and "View History" navigation
  - Dark mode support across all new templates
  - 31 new tests added (9 model + 10 command + 12 view tests)
  - All 247 tests passing ✅ (216 existing + 31 new Phase 6)
  - Storage: ~400 KB for 10 years of data (highly efficient)
  - Query performance: <200ms for stock history, <300ms for comparison report
  - Fully backwards compatible with existing CuratedStock model
  - Complete DCF assumptions stored with each snapshot (14 fields)
- **Next**: Consider Phase 6.1 (Visualizations and Advanced Analytics) or Phase 7 (Individual Stock Options Scanning):
  - Phase 6.1: Chart.js visualizations, advanced analytics (volatility, CAGR, correlation), REST API
  - Phase 7: User-driven individual stock scanning with ticker input form
  - See `reference/ROADMAP.md` for detailed phase descriptions
  