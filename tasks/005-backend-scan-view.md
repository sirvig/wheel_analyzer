# Task 005: Implement Backend View for Manual Scan

## Progress Summary

**Status**: Completed

- [x] Step 1: Create `scan_view` in `scanner/views.py`
- [x] Step 2: Implement Redis Locking Mechanism
- [x] Step 3: Integrate `perform_scan()` Function
- [x] Step 4: Add URL Pattern

## Overview

This task involves creating the backend infrastructure needed to trigger a manual scan from the web interface. This includes a new Django view that will handle the request, manage the scan status using a Redis lock, and execute the scan logic.

## Implementation Steps

### Step 1: Create `scan_view` in `scanner/views.py`

- Create a new function-based view named `scan_view` in the `scanner/views.py` file.
- This view will be designed to handle POST requests initiated by the user clicking the scan button.

**Files to modify:**

- `scanner/views.py`

### Step 2: Implement Redis Locking Mechanism

- Within the `scan_view`, implement a locking mechanism using Redis to ensure only one scan runs at a time.
- Before starting a scan, the view will check for a specific key (e.g., `scan_in_progress`) in Redis.
- If the key exists, the view will return an HTML partial indicating that a scan is already running.
- If the key does not exist, the view will set it with a timeout and proceed with the scan. The timeout prevents the lock from getting stuck if the process fails.
- A `finally` block will be used to ensure the lock is released after the scan is complete or if an error occurs.

**Files to modify:**

- `scanner/views.py`

### Step 3: Integrate `perform_scan()` Function

- The `scan_view` will call the `perform_scan()` function (created in Task 004) to execute the actual scan.
- Upon successful completion, the view will render the `scanner/options_list.html` partial with the new data and return it.
- In case of an error during the scan, the view will log the error and return an HTML partial with an error message.

**Files to modify:**

- `scanner/views.py`

### Step 4: Add URL Pattern

- Create a new URL pattern in `scanner/urls.py` that maps a URL (e.g., `/scanner/scan/`) to the `scan_view`.
- The URL will be named (e.g., `name='scan'`) so it can be easily referenced in templates.

**Files to modify:**

- `scanner/urls.py`

## Acceptance Criteria

- [x] A new `scan_view` is created in `scanner/views.py`.
- [x] The view correctly uses a Redis lock to prevent concurrent scans.
- [x] The view successfully calls the `perform_scan()` function and handles both success and error responses.
- [x] A new URL is added to `scanner/urls.py` that correctly routes to the `scan_view`.
- [x] Sending a POST request to the new URL triggers a scan and returns the appropriate HTML partial.

## Implementation Notes

- Created `scan_view()` function in `scanner/views.py` with `@require_POST` decorator
- Implemented Redis locking mechanism using key `scan_in_progress` with 600-second (10-minute) timeout
- Lock prevents concurrent scans and provides user-friendly error message
- View calls `perform_scan(debug=False)` from Task 004
- Returns different responses based on scan result:
  - **Success**: Renders `scanner/partials/options_results.html` with updated scan data
  - **Already running**: Yellow alert message indicating scan in progress
  - **Market closed**: Blue info message explaining market hours
  - **Error**: Red error message with user-friendly text, details logged server-side
- Lock is released in `finally` block to prevent stuck locks
- Added URL pattern `/scanner/scan/` with name `scan` in `scanner/urls.py`
- Created new partial template `templates/scanner/partials/options_results.html`
- Updated `index` view to render `scanner/index.html` and use the partial template
- Simplified and cleaned up the index view logic, removing duplicate code
- All error messages use Tailwind CSS alert styling consistent with the project
