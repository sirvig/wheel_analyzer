# Task 001: Create CuratedStock Model and Admin

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create CuratedStock Model
- [ ] Step 2: Create CuratedStock Admin
- [ ] Step 3: Generate Database Migration

## Overview

This task is to create the `CuratedStock` model and a Django admin interface to manage the curated list of stocks.

## Implementation Steps

### Step 1: Create CuratedStock Model

- Create a new `CuratedStock` model in `scanner/models.py`.
- The model should have the following fields:
    - `symbol`: `CharField` with `max_length=10` and `unique=True`.
    - `created_at`: `DateTimeField` with `auto_now_add=True`.
    - `updated_at`: `DateTimeField` with `auto_now=True`.

**Files to modify:**

- `scanner/models.py`

### Step 2: Create CuratedStock Admin

- Register the `CuratedStock` model in `scanner/admin.py`.
- Create a `CuratedStockAdmin` class to display `symbol`, `created_at`, and `updated_at` in the list view.

**Files to modify:**

- `scanner/admin.py`

### Step 3: Generate Database Migration

- Run `python manage.py makemigrations scanner` to generate the migration file for the new model.

**Files to create:**

- `scanner/migrations/XXXX_auto_...py`

## Acceptance Criteria

- [ ] `CuratedStock` model is created in `scanner/models.py` with the specified fields.
- [ ] The `CuratedStock` model is registered with the Django admin.
- [ ] An admin class `CuratedStockAdmin` is created and configured.
- [ ] A database migration is successfully generated for the `CuratedStock` model.
- [ ] It is possible to create, view, update, and delete `CuratedStock` objects through the Django admin interface after applying the migration.
