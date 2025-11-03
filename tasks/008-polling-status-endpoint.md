# Task 008: Create Polling Status Endpoint

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Create New URL for Status Check
- [x] Step 2: Implement `scan_status` View
- [x] Step 3: Create Polling Partial Template

## Overview

This task involves creating the backend endpoint that the frontend will poll to check the status of a running scan. The endpoint will check for the existence of the Redis scan lock and return one of two responses: an "in-progress" message if the scan is still running, or the final results if the scan is complete.

## Implementation Steps

### Step 1: Create New URL for Status Check

- In `scanner/urls.py`, add a new path for the polling endpoint.
- The URL should be something like `scan-status/` and be named `scan_status` for easy reference.

**Files to modify:**

- `scanner/urls.py`

### Step 2: Implement `scan_status` View

- In `scanner/views.py`, create a new view function called `scan_status`.
- This view will check for the existence of the `SCAN_LOCK_KEY` in Redis.
- **If the lock exists:** The view should return the `scanner/partials/scan_polling.html` partial. This response must contain the polling `div` so that the polling continues.
- **If the lock does not exist:** The scan is complete. The view should fetch the latest scan results from the Redis cache and render the final `scanner/partials/options_results.html` partial.

**Files to modify:**

- `scanner/views.py`

### Step 3: Create Polling Partial Template

- Create a new template file `templates/scanner/partials/scan_polling.html`.
- This template will contain the user-facing "in-progress" message and the HTMX attributes to enable polling.
- The root element of this partial will look similar to this:
  ```html
  <div hx-get="{% url 'scanner:scan_status' %}" hx-trigger="load, every 15s" hx-swap="outerHTML">
      <p>Scan in progress...</p>
  </div>
  ```

**Files to create:**

- `templates/scanner/partials/scan_polling.html`

## Acceptance Criteria

- [x] A new URL `/scanner/scan-status/` is added to `scanner/urls.py`.
- [x] A new `scan_status` view is implemented in `scanner/views.py`.
- [x] When a scan is in progress, a GET request to `/scanner/scan-status/` returns the polling partial, keeping the poll alive.
- [x] When a scan is complete, a GET request to `/scanner/scan-status/` returns the `options_results.html` partial, which stops the poll.
- [x] A new `scan_polling.html` partial is created and used for the in-progress response.

## Summary of Changes

**Files Created:**
- `templates/scanner/partials/scan_polling.html` - Polling partial with progressive results display

**Files Modified:**
- `scanner/urls.py` - Added `scan-status/` URL pattern
- `scanner/views.py` - Added `scan_status()` view function
- `scanner/templatetags/options_extras.py` - Added `split` template filter

**Key Changes:**

1. **URL Pattern (`scanner/urls.py`):**
   - Added `path("scan-status/", views.scan_status, name="scan_status")`

2. **scan_status View (`scanner/views.py`):**
   - Checks if `SCAN_LOCK_KEY` exists in Redis
   - Fetches current results using `get_scan_results()` helper function
   - Returns `scan_polling.html` if lock exists (scan in progress)
   - Returns `options_results.html` if lock doesn't exist (scan complete)

3. **scan_polling.html Template:**
   - HTMX attributes: `hx-get`, `hx-trigger="load delay:15s, every 15s"`, `hx-swap="outerHTML"`
   - Animated status banner with pulse effect (per requirement 3b)
   - Displays simplified progress: "Scan in progress... (45% complete)" (per requirement 2b)
   - Handles error states by showing error message from `last_run` Redis key (per requirement 4c)
   - Shows progressive results with same accordion structure as final results
   - Messages adapt based on content: "No options found yet. Scanning..." vs "Results updating in real-time"

4. **Template Filter (`options_extras.py`):**
   - Added `split` filter to parse progress percentage from "Currently Running - XX.XX% completed"
