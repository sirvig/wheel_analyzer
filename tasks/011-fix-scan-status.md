# Task 011: Fix Scan Status Display

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Update scan_view to set initial status
- [x] Step 2: Simplify scan_polling.html template logic
- [x] Step 3: Update completion message in background scan
- [ ] Step 4: Test scan status flow (manual testing required)

## Overview

This task fixes a bug where clicking "Scan for Options" immediately displays cached status from the previous scan (like "Market is closed" or error messages) instead of showing the current scan's status. The issue is in the `scan_polling.html` template's `elif` statement that displays `last_scan` cache values immediately.

**Related Bug:** Reference BUGS.md - "When clicking the 'Scan for Options' button, the last run is immediately placed in the status banner. It should not display the last run information, it should display the current status of the scan."

## Implementation Steps

### Step 1: Update scan_view to set initial status

- Open `scanner/views.py`
- Locate the `scan_view(request)` function
- After line 138 where the scan lock is set (`r.setex(SCAN_LOCK_KEY, SCAN_LOCK_TIMEOUT, "1")`), add code to immediately set the initial scanning status
- Set `last_run` to "Scanning in progress..." before starting the background thread
- This ensures the polling template shows the correct initial status

**Files to modify:**
- `scanner/views.py`

**Code to add (after line 138):**
```python
# Set initial status before starting scan
r.set("last_run", "Scanning in progress...")
```

### Step 2: Simplify scan_polling.html template logic

- Open `templates/scanner/partials/scan_polling.html`
- Review lines 6-20 (the status banner conditional logic)
- The `elif` statement (lines 15-17) displays old cached errors/messages - this is the bug
- Simplify the logic to:
  - If "Currently Running" with percentage → show percentage
  - Else → show "Scanning in progress..."
- Remove the `elif` clause that checks for "Market is closed" or "error"

**Files to modify:**
- `templates/scanner/partials/scan_polling.html`

**Current problematic code (lines 15-17):**
```django
{% elif "Market is closed" in last_scan or "error" in last_scan or "An error occurred" in last_scan %}
    <!-- Error state (4c: Display error message from last_run) -->
    {{ last_scan }}
```

**Should be simplified to remove the elif block entirely.**

### Step 3: Update completion message in background scan

- Open `scanner/views.py`
- Locate the `run_scan_in_background()` function
- Find the success block (around line 66-68)
- Update the success message to include timestamp
- Change from logging-only to setting `last_run` with completion message

**Files to modify:**
- `scanner/views.py`

**Code to update (around lines 65-68):**
```python
from datetime import datetime

if result["success"]:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completion_message = f"Scan completed successfully at {timestamp}"
    r.set("last_run", completion_message)
    logger.info(f"Background scan completed successfully: {result['scanned_count']} tickers")
```

### Step 4: Test scan status flow

- Click "Scan for Options" button
- Verify initial status shows "Scanning in progress..."
- Verify NO old error messages appear
- Monitor polling updates during scan
- Verify completion message appears with timestamp when done
- Test error scenario (market closed) to ensure errors still display correctly

## Acceptance Criteria

- [ ] Clicking "Scan for Options" immediately shows "Scanning in progress..." (not cached old messages)
- [ ] Status banner does not display previous scan's error messages or "Market is closed" when new scan starts
- [ ] If scan progress includes percentage, it displays correctly (e.g., "Scan in progress... (23% complete)")
- [ ] When scan completes successfully, shows "Scan completed successfully at [timestamp]"
- [ ] Error handling still works - if NEW scan fails, error message displays correctly
- [ ] Polling mechanism continues to work as expected

## Testing Checklist

### Initial Status Tests:
- [ ] Click "Scan for Options" → immediately see "Scanning in progress..."
- [ ] Verify NO "Market is closed" message appears when starting new scan
- [ ] Verify NO old error messages appear when starting new scan

### During Scan Tests:
- [ ] Status updates every 15 seconds during scan
- [ ] If percentage data available, shows "Scan in progress... (XX% complete)"
- [ ] Accordion results update in real-time as tickers are scanned

### Completion Tests:
- [ ] When scan completes, status changes to "Scan completed successfully at [timestamp]"
- [ ] Timestamp format is readable (YYYY-MM-DD HH:MM:SS)
- [ ] Polling stops when scan is complete
- [ ] Final results display correctly

### Error Handling Tests:
- [ ] Trigger scan during market closed hours
- [ ] Verify error message displays after scan attempt (not before)
- [ ] Previous successful scan data should remain visible
- [ ] Error message should be clear and informative

## Notes

- The bug occurs because `scan_polling.html` checks for cached `last_scan` values before checking scan status
- The `elif` clause was meant for error display but shows OLD errors from previous scans
- The fix ensures `last_run` is set to "Scanning in progress..." BEFORE the template renders
- This maintains real-time status updates while preventing stale data display

## Summary of Changes

**Files Modified:**
- `scanner/views.py` - Updated `scan_view()` and `run_scan_in_background()`
- `templates/scanner/partials/scan_polling.html` - Simplified status banner logic

**Key Changes:**

1. **scan_view() Function (scanner/views.py):**
   - Added `r.set("last_run", "Scanning in progress...")` after acquiring scan lock
   - Ensures initial status is set before returning polling template
   - Prevents display of stale cached status messages

2. **run_scan_in_background() Function (scanner/views.py):**
   - Added import: `from datetime import datetime`
   - Updated success block to set completion message with timestamp
   - Format: "Scan completed successfully at YYYY-MM-DD HH:MM:SS"
   - Maintains existing error handling for failed scans

3. **scan_polling.html Template:**
   - Removed `elif` clause that displayed cached error/closed market messages
   - Simplified logic to only show:
     - Percentage if "Currently Running - XX.XX% completed" format
     - Default "Scanning in progress..." otherwise
   - Error messages from NEW scans still display correctly (set by background thread)

**User Experience Flow:**
1. User clicks "Scan for Options" button
2. **Immediately** sees "Scanning in progress..." (NEW - was showing old errors)
3. Status updates every 15 seconds during scan
4. Progress percentage displays if available
5. When complete, shows "Scan completed successfully at [timestamp]"
6. If error occurs during THIS scan, error message displays appropriately
