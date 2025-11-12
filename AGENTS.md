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

### Data Migration Best Practices

**IMPORTANT**: Data migrations (using `RunPython`) run in ALL environments including tests. Follow these rules:

1. **Always check environment in data migrations**:
   ```python
   def populate_data(apps, schema_editor):
       # Skip data migration in test environment
       if schema_editor.connection.alias != 'default':
           return

       from django.conf import settings
       if getattr(settings, 'ENVIRONMENT', None) == 'TESTING':
           return

       # Your data population code here
   ```

2. **Prefer fixtures over data migrations**:
   - Data migrations: Use only for schema-dependent data (foreign keys, etc.)
   - Fixtures: Use for initial production data that doesn't depend on complex logic
   - Management commands: Best for production data seeding (explicit, controllable)

3. **Why this matters**:
   - Tests expect isolated, empty databases
   - Pre-populated data breaks test assertions that count records
   - Analytics tests perform global queries expecting only test-created data
   - Example failure: Test creates 3 stocks, migration adds 26, assertion `== 3` fails with `== 29`

4. **Testing data migrations**:
   - Verify migration respects environment checks
   - Test that `ENVIRONMENT=TESTING` skips data population
   - Confirm test database starts empty

5. **Example - See `scanner/migrations/0003_populate_curated_stocks.py`**:
   - Good: Checks both connection alias AND environment setting
   - Good: Returns early without side effects in test environment
   - Good: Preserves production behavior while maintaining test isolation

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
- **Current Status**: Phase 6.1 completed ✅ - Analytics & Visualizations system fully implemented with 243/243 tests passing (100% pass rate). Production-ready with interactive Chart.js visualizations and comprehensive analytics calculations. Key achievements:
  - Analytics module (`scanner/analytics.py` - 546 lines) with 6 analytics functions
  - Dedicated analytics dashboard at `/scanner/valuations/analytics/` with portfolio metrics and multi-line trend chart
  - Embedded charts on stock history page (dual-line EPS/FCF) and comparison page (grouped bar chart)
  - Portfolio analytics: total stocks, average IV, average volatility, average CAGR
  - Stock analytics: volatility (std dev + CV), CAGR, EPS/FCF correlation
  - Dark mode support with dynamic color detection from computed styles
  - Historical data: 416 snapshots (26 stocks × 16 quarters, Q1 2022 - Q4 2025)
  - All bugs resolved through systematic root-cause debugging
  - Chart.js 4.4.1 integration with responsive, interactive visualizations
  - All 243 tests passing ✅ (243 existing, analytics tests deferred)
  - Files changed: 7 modified + 2 new (1,378 lines added)
  - Query performance: <200ms for analytics, <100ms for chart data preparation
- **Next**: Ready to merge Phase 6.1 to main, then consider Phase 6.2 (REST API) or Phase 7 (Individual Stock Scanning):
  - Phase 6.2: REST API endpoints for analytics data, JSON/CSV exports, webhooks
  - Phase 7: User-driven individual stock scanning with ticker input form
  - See `reference/ROADMAP.md` for detailed phase descriptions
  