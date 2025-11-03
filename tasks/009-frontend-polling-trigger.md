# Task 009: Update Frontend to Trigger Polling

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Update `scan_view` Response
- [x] Step 2: Adjust `index.html` Target Area

## Overview

This task connects the backend changes to the frontend. The `scan_view` will be updated to return the new polling partial, and the main scanner template will be adjusted to ensure the polling UI is correctly inserted into the page.

## Implementation Steps

### Step 1: Update `scan_view` Response

- Modify the `scan_view` in `scanner/views.py`.
- After starting the background scan thread (Task 007), the view must now render and return the `scanner/partials/scan_polling.html` template created in Task 008.
- This response will replace the target `div` on the main page and kick off the polling process.

**Files to modify:**

- `scanner/views.py`

### Step 2: Adjust `index.html` Target Area

- Review `templates/scanner/index.html`.
- The `hx-target` attribute on the "Scan for Options" button points to a `div` (e.g., `#scan-results`).
- Ensure this `div` is structured correctly to be replaced by the `scan_polling.html` partial and then subsequently by the `options_results.html` partial.
- The `hx-swap` method should be `outerHTML` to ensure the polling `div` is completely replaced by the final results, which correctly terminates the poll.

**Files to modify:**

- `templates/scanner/index.html`

## Acceptance Criteria

- [x] Clicking the "Scan for Options" button now immediately returns the `scan_polling.html` partial.
- [x] The UI shows an "in progress" message and begins polling the `/scanner/scan-status/` endpoint.
- [x] The `hx-swap="outerHTML"` attribute is used to ensure the polling mechanism is correctly terminated.
- [x] From the user's perspective, clicking the button starts a loading state that automatically resolves to the final results list after the scan is complete.

## Summary of Changes

**Files Modified:**
- `scanner/views.py` - Already updated in Task 007
- `templates/scanner/index.html` - Changed hx-swap attribute

**Key Changes:**

1. **scan_view Response (`scanner/views.py`):**
   - Already implemented in Task 007
   - After starting background thread, calls `get_scan_results()` to fetch current data
   - Returns `render(request, "scanner/partials/scan_polling.html", context)`
   - This kicks off the polling process immediately

2. **index.html Button Configuration:**
   - Changed `hx-swap="innerHTML"` to `hx-swap="outerHTML"`
   - This ensures:
     - The entire `#scan-results` div is replaced by the polling partial
     - The polling partial's HTMX attributes take effect
     - When scan completes, the polling div is replaced with final results
     - Polling automatically terminates when final results are returned

**User Experience Flow:**
1. User clicks "Scan for Options" button
2. Button shows loading spinner (HTMX built-in indicator)
3. Immediately replaced with animated "Scan in progress..." banner
4. Current options results display below (from previous scan or empty)
5. Every 15 seconds, view auto-refreshes with updated results
6. Progress percentage updates: "Scan in progress... (23% complete)"
7. As backend scans each ticker, options appear in real-time
8. When scan completes, polling stops and final results display (no more pulse animation)
