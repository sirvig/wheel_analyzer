# Task 002: Data Migration for Curated Stocks

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create Empty Migration File
- [ ] Step 2: Implement Data Migration Logic
- [ ] Step 3: Apply Migrations

## Overview

This task is to create a data migration to populate the `CuratedStock` table with data from the `scanner/data/options.json` file.

## Implementation Steps

### Step 1: Create Empty Migration File

- Run `python manage.py makemigrations scanner --empty --name populate_curated_stocks` to create a new empty migration file.

**Files to create:**

- `scanner/migrations/XXXX_populate_curated_stocks.py`

### Step 2: Implement Data Migration Logic

- In the newly created migration file, write a Python script to:
    1. Read the `scanner/data/options.json` file.
    2. Extract the list of stock tickers from the `put` key.
    3. For each ticker, create a new `CuratedStock` object and save it to the database.

**Files to modify:**

- `scanner/migrations/XXXX_populate_curated_stocks.py`

### Step 3: Apply Migrations

- Run `python manage.py migrate scanner` to apply the new data migration.

## Acceptance Criteria

- [ ] A new data migration file is created in `scanner/migrations`.
- [ ] The migration script successfully reads the `options.json` file and populates the `CuratedStock` table.
- [ ] After running the migration, the `CuratedStock` table contains all the tickers from the `options.json` file.
