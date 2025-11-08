# Wheel Analyzer

A Django-based web application for tracking and analyzing stock options trading, specifically focused on the "wheel strategy" (selling puts, taking assignment, selling calls). The application helps track options campaigns, individual transactions, and scan for new trading opportunities.

## Project Status

**Current Phase**: Phase 5 - Visual Intrinsic Value Indicators (Planning Complete)

### Completed Features
- ✅ **Phase 1**: Database-driven curated stock list with admin interface
- ✅ **Phase 2**: Manual options scan trigger with HTMX integration
- ✅ **Phase 3**: Real-time scan progress polling with progressive results
- ✅ **Phase 4**: DCF intrinsic value calculations (EPS and FCF methods)
- ✅ **Phase 4.1**: API rate limit optimization with smart stock selection

### In Progress
- ⏳ **Phase 5**: Visual intrinsic value indicators and valuations page
  - Planning complete (5 task files created)
  - Implementation not yet started
  - Next: Begin Task 024 (Add Intrinsic Value Context)

### Key Capabilities
- **Options Scanner**: Find options with 30%+ annualized returns and delta < 0.20
- **Intrinsic Value Calculation**: Dual DCF models (EPS-based and FCF-based)
- **Campaign Tracking**: Track complete wheel strategy campaigns per stock
- **Transaction Management**: Record puts, calls, rolls, assignments, and dividends
- **Smart API Usage**: Respects AlphaVantage rate limits with rolling updates

## Technology Stack

- **Backend**: Django 5.1+, Python 3.13+
- **Database**: PostgreSQL 14.1
- **Cache/Queue**: Redis 6.2
- **Frontend**: HTMX, vanilla JavaScript, Bootstrap 5
- **Package Management**: uv (fast Python package installer)
- **Task Runner**: just (Makefile alternative in Rust)
- **Deployment**: Docker with docker-compose
- **Linting/Formatting**: ruff
- **Testing**: pytest-django

## Local Development

The local development environment runs in a Docker container with source mounted directly. The Django development server will reload on any change.

### First Time Setup

1. Copy environment file:
   ```shell
   cp .env.example .env
   ```

2. Create Docker network:
   ```shell
   docker network create app_main
   ```

3. Build and start services:
   ```shell
   docker-compose up -d --build
   ```

4. Run migrations:
   ```shell
   just exec python manage.py migrate
   ```

5. Create superuser:
   ```shell
   just exec python manage.py createsuperuser
   ```

### Development Commands

This project uses [Just](https://github.com/casey/just) as the task runner.

List all available commands:
```shell
just --list
```

#### Essential Commands

- `just test` - Run pytest test suite
- `just lint` - Format and check code with ruff
- `just run` - Start Django development server (local, not Docker)
- `just up` - Start Docker services (PostgreSQL and Redis)
- `just kill` - Stop Docker services

#### Django Management

- `just exec python manage.py makemigrations` - Generate migrations
- `just exec python manage.py migrate` - Apply migrations
- `just exec python manage.py shell` - Django shell

#### Custom Management Commands

- `just scan` - Run options scanner (cron_scanner)
- `just sma` - Calculate simple moving averages
- `python manage.py calculate_intrinsic_value` - Calculate DCF intrinsic values

### Linters

Format code with ruff:
```shell
just lint
```

### Migrations

Create migrations:
```shell
just exec python manage.py makemigrations
```

Apply migrations:
```shell
just exec python manage.py migrate
```

Downgrade migrations:
```shell
just exec python manage.py showmigrations
just exec python manage.py migrate <app> <migration_number>
```

### Tests

All tests are integration tests requiring database connection.

Run tests:
```shell
just test
```

Run specific test file:
```shell
just test scanner/tests/test_scanner_views.py
```

Auto-run tests on file changes:
```shell
just test-watch
```

### Database Backup and Restore

Using `pg_dump` and `pg_restore`:

Backup:
```shell
just backup
# Creates: /backups/backup-YYYY-MM-DD-HHMMSS.dump.gz
```

Copy backup to local machine:
```shell
just mount-docker-backup  # Get all backups
just mount-docker-backup backup-YYYY-MM-DD-HHMMSS.dump.gz  # Get specific backup
```

Restore:
```shell
just restore backup-YYYY-MM-DD-HHMMSS.dump.gz
```

## Project Architecture

### Django Apps

**tracker**: Options trading campaign and transaction tracking
- Models: `User`, `Account`, `Campaign`, `Transaction`
- Tracks complete trading history per campaign

**scanner**: Options scanning and intrinsic value analysis
- Models: `CuratedStock`, `OptionsWatch`
- External integrations: Market data API, Alpha Vantage API
- DCF valuation calculations (EPS and FCF methods)

### Key Features

**Options Scanner**:
- Scans curated stock list for attractive options
- Filters: 30%+ annualized return, delta < 0.20
- Real-time progress updates via HTMX polling
- Redis caching for performance

**Intrinsic Value Calculator**:
- Dual DCF models: EPS-based and FCF-based
- Fetches fundamental data from Alpha Vantage
- Smart stock selection respecting API rate limits
- 7-day Redis caching
- Daily rolling updates (7 stocks/day)

**Campaign Tracker**:
- Track complete wheel strategy campaigns
- Support for puts, calls, rolls, assignments, dividends
- Per-account and per-stock organization

## Documentation

- **AGENTS.md**: AI assistant context and development guidelines
- **reference/ROADMAP.md**: Project roadmap and phase tracking
- **tasks/**: Numbered task files with implementation details
- **Session Summaries**: Daily session summaries in root directory

## Development Workflow

See `AGENTS.md` for detailed development workflow, including:
- Task-based development process
- Testing requirements
- Code conventions
- Migration workflow

## Next Steps

1. Implement Task 024: Add intrinsic value context to scanner views
2. Implement Task 025: Add visual indicators (Bootstrap badges) to options results
3. Implement Task 026: Create valuations page backend
4. Implement Task 027: Create valuations page frontend
5. Implement Task 028: Testing and refinement

See `reference/ROADMAP.md` and individual task files in `/tasks` for detailed specifications.

## License

[Your license here]

## Contributing

[Your contributing guidelines here]
