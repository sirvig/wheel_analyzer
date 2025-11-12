"""
Create quarterly valuation snapshots for curated stocks.

This command captures quarterly snapshots (Jan 1, Apr 1, Jul 1, Oct 1) of
intrinsic value calculations and DCF assumptions from the CuratedStock model
into the ValuationHistory model.

Usage:
    # Create snapshot for current quarter
    python manage.py create_quarterly_valuation_snapshot

    # Create snapshot for specific date
    python manage.py create_quarterly_valuation_snapshot --date 2025-01-01

    # Create snapshot for specific stocks
    python manage.py create_quarterly_valuation_snapshot --symbols AAPL MSFT

    # Preview without creating
    python manage.py create_quarterly_valuation_snapshot --dry-run

    # Force overwrite existing snapshots
    python manage.py create_quarterly_valuation_snapshot --force

Schedule:
    Run quarterly via cron on Jan 1, Apr 1, Jul 1, Oct 1:
    0 23 1 1,4,7,10 * cd /path/to/project && python manage.py create_quarterly_valuation_snapshot
"""

import logging
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from scanner.models import CuratedStock, ValuationHistory

logger = logging.getLogger(__name__)

# Quarterly snapshot dates (month, day)
QUARTERLY_DATES = [(1, 1), (4, 1), (7, 1), (10, 1)]


class Command(BaseCommand):
    help = "Create quarterly valuation snapshots for curated stocks"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Snapshot date (YYYY-MM-DD), defaults to current quarter date'
        )
        parser.add_argument(
            '--symbols',
            nargs='+',
            type=str,
            help='Specific stock symbols to snapshot (default: all active)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing snapshots for the given date'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without writing to database'
        )

    def handle(self, *args, **options):
        """Main command execution."""
        logger.info("=" * 60)
        logger.info("Starting quarterly valuation snapshot creation")
        logger.info(f"Options: {options}")
        logger.info("=" * 60)

        # Determine snapshot date
        if options.get('date'):
            try:
                snapshot_date = date.fromisoformat(options['date'])
            except ValueError:
                raise CommandError(f"Invalid date format: {options['date']}. Use YYYY-MM-DD")
        else:
            snapshot_date = self._get_current_quarter_date()

        self.stdout.write(f"Snapshot date: {snapshot_date.isoformat()}")

        # Validate it's a quarterly date
        if (snapshot_date.month, snapshot_date.day) not in QUARTERLY_DATES:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Warning: {snapshot_date} is not a standard quarterly date "
                    f"(Jan 1, Apr 1, Jul 1, Oct 1)"
                )
            )

        # Get stocks to snapshot
        if options.get('symbols'):
            stocks = CuratedStock.objects.filter(
                symbol__in=[s.upper() for s in options['symbols']]
            )
            if not stocks.exists():
                raise CommandError(
                    f"No stocks found with symbols: {', '.join(options['symbols'])}"
                )
        else:
            stocks = CuratedStock.objects.filter(active=True)

        total_stocks = stocks.count()
        self.stdout.write(f"Processing {total_stocks} stock(s)...")

        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        # Process each stock
        created = 0
        skipped = 0
        errors = 0

        for stock in stocks:
            try:
                result = self._create_snapshot(
                    stock=stock,
                    snapshot_date=snapshot_date,
                    force=options.get('force', False),
                    dry_run=options.get('dry_run', False)
                )

                if result == 'created':
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {stock.symbol}: Snapshot created")
                    )
                elif result == 'skipped':
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ⊘ {stock.symbol}: Snapshot already exists")
                    )
                elif result == 'no_data':
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⊘ {stock.symbol}: No valuation data to snapshot"
                        )
                    )
            except Exception as e:
                errors += 1
                logger.error(f"Error creating snapshot for {stock.symbol}: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"  ✗ {stock.symbol}: Error - {str(e)}"))

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 65}"))
        self.stdout.write(self.style.SUCCESS("SUMMARY:"))
        self.stdout.write(f"  Snapshot date: {snapshot_date.isoformat()}")
        self.stdout.write(f"  Total stocks: {total_stocks}")
        self.stdout.write(self.style.SUCCESS(f"  Created: {created}"))
        self.stdout.write(self.style.WARNING(f"  Skipped: {skipped}"))
        self.stdout.write(self.style.ERROR(f"  Errors: {errors}"))

        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING("\n  (DRY RUN - No changes were made)"))

        self.stdout.write(self.style.SUCCESS(f"{'=' * 65}\n"))

        logger.info(f"Snapshot creation complete: {created} created, {skipped} skipped, {errors} errors")

    def _get_current_quarter_date(self):
        """
        Get the current quarter snapshot date (Jan 1, Apr 1, Jul 1, Oct 1).

        Returns:
            date: The snapshot date for the current quarter
        """
        today = date.today()
        year = today.year

        # Determine which quarter we're in
        if today.month < 4:
            return date(year, 1, 1)
        elif today.month < 7:
            return date(year, 4, 1)
        elif today.month < 10:
            return date(year, 7, 1)
        else:
            return date(year, 10, 1)

    @transaction.atomic
    def _create_snapshot(self, stock, snapshot_date, force=False, dry_run=False):
        """
        Create a valuation snapshot for a single stock.

        Args:
            stock: CuratedStock instance
            snapshot_date: date object for the snapshot
            force: Whether to overwrite existing snapshot
            dry_run: Whether to preview without creating

        Returns:
            str: 'created', 'skipped', or 'no_data'
        """
        # Check if snapshot already exists
        existing = ValuationHistory.objects.filter(
            stock=stock,
            snapshot_date=snapshot_date
        ).first()

        if existing and not force:
            return 'skipped'

        # Check if stock has valuation data to snapshot
        if stock.intrinsic_value is None and stock.intrinsic_value_fcf is None:
            return 'no_data'

        # Preview in dry-run mode
        if dry_run:
            return 'created'  # Would be created

        # Delete existing if force=True
        if existing and force:
            existing.delete()
            logger.info(f"Deleted existing snapshot for {stock.symbol} on {snapshot_date}")

        # Create new snapshot from current CuratedStock values
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=snapshot_date,
            # EPS values
            intrinsic_value=stock.intrinsic_value,
            current_eps=stock.current_eps,
            eps_growth_rate=stock.eps_growth_rate,
            eps_multiple=stock.eps_multiple,
            # FCF values
            intrinsic_value_fcf=stock.intrinsic_value_fcf,
            current_fcf_per_share=stock.current_fcf_per_share,
            fcf_growth_rate=stock.fcf_growth_rate,
            fcf_multiple=stock.fcf_multiple,
            # Shared assumptions
            desired_return=stock.desired_return,
            projection_years=stock.projection_years,
            preferred_valuation_method=stock.preferred_valuation_method,
        )

        logger.info(f"Created snapshot for {stock.symbol} on {snapshot_date}")
        return 'created'
