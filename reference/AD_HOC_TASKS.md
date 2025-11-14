# Ad-hoc tasks

Completed:
- ✅ On /scanner/ clicking "Scan for Options" triggers a background thread according to the logs but it does not actually appear to be running.  We need an admin page available to the staff which will show the current status of the scanning operation (background thread) and will allow us to clear the lock flags in Redis if a scan failed.
  - **Solution**: Created staff-only scan monitoring page at `/scanner/admin/monitor/` with:
    - Real-time Redis lock state monitoring (locked/clear, TTL)
    - Database scan status tracking (ScanStatus model)
    - "Clear Lock" button that deletes Redis lock AND marks active scans as aborted
    - Auto-refresh every 10 seconds
    - Full CRUD via Django admin interface
    - 21 comprehensive tests (100% pass rate)
  - **Files Changed**: 11 files, ~900 lines added
    - New model: `ScanStatus` (status, scan_type, timestamps, result counts)
    - New views: `scan_monitor_view()`, `clear_scan_lock_view()`
    - Updated: `run_scan_in_background()` to persist scan status
    - New templates: `scan_monitor.html`, `lock_cleared_message.html`
    - Migration: `0010_scanstatus.py`
    - Tests: `test_scan_status.py` (21 tests)

Pending:

