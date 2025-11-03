# Task 007: Refactor Scan View for Asynchronous Execution

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Modify `scan_view` to be Asynchronous
- [x] Step 2: Create a Thread Target Function
- [x] Step 3: Ensure Lock Is Released by Thread

## Overview

To enable polling, the long-running scan process must not block the initial web request. This task refactors the `scan_view` to execute the options scan in a background thread using Python's built-in `threading` module. This change is the foundation for the polling mechanism.

## Implementation Steps

### Step 1: Modify `scan_view` to be Asynchronous

- Import the `threading` module in `scanner/views.py`.
- The `scan_view` should no longer call `perform_scan()` directly.
- Instead, it will be responsible for setting the Redis lock, starting the background thread, and immediately returning an initial HTML partial to the user that will trigger the polling.

**Files to modify:**

- `scanner/views.py`

### Step 2: Create a Thread Target Function

- Create a new helper function (e.g., `run_scan_in_background`) that will be the target for the `threading.Thread`.
- This function will contain the logic to call `perform_scan()` and, crucially, to release the Redis lock when the scan is finished.

**Files to modify:**

- `scanner/views.py`

### Step 3: Ensure Lock Is Released by Thread

- The responsibility for releasing the Redis lock (`scan_in_progress`) must move from the `scan_view` to the new background thread function.
- Use a `try...finally` block within the thread's target function to ensure that `r.delete(SCAN_LOCK_KEY)` is called, even if the `perform_scan` function encounters an error. This prevents the lock from getting stuck.

**Files to modify:**

- `scanner/views.py`

## Acceptance Criteria

- [x] The `scan_view` in `scanner/views.py` is updated to import `threading`.
- [x] When `scan_view` is called, it sets the Redis lock (`scan_in_progress`).
- [x] `scan_view` starts a new background thread that executes the `perform_scan` function.
- [x] `scan_view` returns an `HttpResponse` immediately, without waiting for the scan to complete.
- [x] The background thread is responsible for deleting the Redis lock upon completion or failure of the scan.

## Summary of Changes

**Files Modified:**
- `scanner/views.py`

**Key Changes:**
1. Added `import threading` at the top of the file
2. Moved `SCAN_LOCK_KEY` and `SCAN_LOCK_TIMEOUT` to module-level constants
3. Created `run_scan_in_background()` function:
   - Executes `perform_scan(debug=False)` in background
   - Releases Redis lock in `finally` block
   - Sets error messages to `last_run` Redis key on failure (per requirement 4c)
4. Created `get_scan_results()` helper function:
   - Extracts Redis result fetching logic into reusable function
   - Used by both `scan_view` and later by `scan_status` view
5. Refactored `scan_view()`:
   - Removed blocking call to `perform_scan()`
   - If scan already in progress, allows user to watch (per requirement 5b)
   - Sets lock and starts background thread with `daemon=True`
   - Immediately returns `scan_polling.html` partial (template to be created in Task 008)
   - No longer blocks waiting for scan completion
