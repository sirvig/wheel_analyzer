# Task 003: Update Scanner to Use CuratedStock Model

## Progress Summary

**Status**: Completed

- [x] Step 1: Update Scanner Logic
- [x] Step 2: Remove JSON File

## Overview

This task is to update the scanner logic to use the `CuratedStock` model instead of the `options.json` file for fetching the list of stocks to scan. After updating the logic, the `options.json` file will be removed.

## Implementation Steps

### Step 1: Update Scanner Logic

- Modify the management commands `cron_sma` and `cron_scanner` to fetch the list of stock tickers from the `CuratedStock` model.
- The code should query the `CuratedStock` model and get a list of all `symbol` values.

**Files to modify:**

- `scanner/management/commands/cron_sma.py`
- `scanner/management/commands/cron_scanner.py`

### Step 2: Remove JSON File

- After updating the code and verifying that the scanner works correctly with the database, delete the `scanner/data/options.json` file.

**Files to delete:**

- `scanner/data/options.json`

## Acceptance Criteria

- [x] The `cron_sma` and `cron_scanner` management commands are updated to use the `CuratedStock` model to get the list of stock tickers.
- [x] The `scanner/data/options.json` file is deleted from the project.
- [x] The scanner functionality remains unchanged and works as expected using the data from the database.

## Implementation Notes

- Updated `cron_sma.py` to query `CuratedStock.objects.filter(active=True).values_list('symbol', flat=True)`
- Updated `cron_scanner.py` to query `CuratedStock.objects.filter(active=True).values_list('symbol', flat=True)`
- Removed imports of `json` and references to `settings.BASE_DIR` from scanner commands
- Deleted `scanner/data/options.json` file
- Created verification command: `scanner/management/commands/verify_curated_stocks.py`
- Verification confirms all 26 stocks are accessible and scanner commands can query them correctly
