# Task 004: Refactor Core Scan Logic

## Progress Summary

**Status**: Completed

- [x] Step 1: Create `scanner/scanner.py`
- [x] Step 2: Move Core Logic to `perform_scan()`
- [x] Step 3: Update `cron_scanner` Command

## Overview

This task involves refactoring the core options scanning logic from the `cron_scanner` management command into a reusable function. This will allow the same logic to be triggered by both the existing management command and the new manual scan view that will be created in a subsequent task.

## Implementation Steps

### Step 1: Create `scanner/scanner.py`

- Create a new file named `scanner.py` inside the `scanner` application directory.

**Files to create:**

- `scanner/scanner.py`

### Step 2: Move Core Logic to `perform_scan()`

- Identify the core scanning logic within the `handle()` method of the `scanner/management/commands/cron_scanner.py` file.
- Move this logic into a new function called `perform_scan()` in the `scanner/scanner.py` file.
- The `perform_scan()` function should encapsulate all the steps of the scan, from fetching stocks to analyzing options and caching the results.

**Files to modify:**

- `scanner/scanner.py`
- `scanner/management/commands/cron_scanner.py`

### Step 3: Update `cron_scanner` Command

- Modify the `cron_scanner` management command to import and call the new `perform_scan()` function.
- Ensure that the command continues to function exactly as it did before the refactoring.

**Files to modify:**

- `scanner/management/commands/cron_scanner.py`

## Acceptance Criteria

- [x] The core scanning logic is successfully extracted into a `perform_scan()` function in `scanner/scanner.py`.
- [x] The `cron_scanner` management command is updated to use the `perform_scan()` function.
- [x] Running `just scan` executes the scan successfully and produces the same output as before the refactor.
- [x] The `cron_scanner` command's code is significantly simplified.

## Implementation Notes

- Created `scanner/scanner.py` with `perform_scan(debug=False)` function
- Extracted all core scanning logic including:
  - Redis connection handling
  - Active stock fetching from CuratedStock model
  - Market hours checking
  - Progress tracking in Redis
  - Options scanning and caching
- Function returns a dictionary with scan results:
  - `success` (bool): Whether scan completed successfully
  - `message` (str): Status message for user feedback
  - `scanned_count` (int): Number of tickers scanned
  - `timestamp` (str): Completion timestamp
  - `error` (str, optional): Error details for debugging
- Updated `cron_scanner.py` to import and call `perform_scan()`
- Command code reduced from ~64 lines to ~31 lines
- Enhanced error handling with try/except and logging
- Maintained all existing functionality including market hours check and progress updates
