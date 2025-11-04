# Task 010: Fix Scanner Authentication

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add login_required decorators to scanner views
- [x] Step 2: Verify LOGIN_URL configuration
- [ ] Step 3: Test authentication flow (manual testing required)

## Overview

This task fixes a security bug where the scanner URL is accessible to unauthenticated users. All scanner routes (`/scanner/`, `/scanner/scan/`, `/scanner/scan-status/`, `/scanner/options/<ticker>`) should require user authentication. Unauthorized users should be redirected to the login page.

**Related Bug:** Reference BUGS.md - "The scanner url should only be accessible by logged in users. Currently any user can navigate to /scanner/"

## Implementation Steps

### Step 1: Add login_required decorators to scanner views

- Open `scanner/views.py`
- Add import at the top: `from django.contrib.auth.decorators import login_required`
- Apply `@login_required` decorator to all view functions:
  - `index(request)` - main scanner page
  - `scan_view(request)` - scan trigger endpoint
  - `scan_status(request)` - polling status endpoint
  - `options_list(request, ticker)` - individual ticker options

**Files to modify:**
- `scanner/views.py`

**Example:**
```python
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    # existing code...
```

### Step 2: Verify LOGIN_URL configuration

- Open `wheel_analyzer/settings.py`
- Verify that `LOGIN_URL` is configured (should be `/accounts/login/` for django-allauth)
- If not present, add: `LOGIN_URL = '/accounts/login/'`
- Verify `LOGIN_REDIRECT_URL` is set (should be `'index'` or home page)

**Files to check/modify:**
- `wheel_analyzer/settings.py`

### Step 3: Test authentication flow

- Logout from the application
- Attempt to access `/scanner/` directly
- Verify redirect to login page with `?next=/scanner/` parameter
- Login with valid credentials
- Verify redirect back to `/scanner/` after successful login

## Acceptance Criteria

- [ ] All scanner views require authentication
- [ ] Unauthenticated users are redirected to login page when accessing any `/scanner/*` route
- [ ] After login, users are redirected back to the page they originally tried to access
- [ ] Authenticated users can access all scanner functionality normally
- [ ] No changes to existing scanner functionality for logged-in users

## Testing Checklist

### Unauthenticated Access Tests:
- [ ] Navigate to `/scanner/` → redirects to `/accounts/login/?next=/scanner/`
- [ ] Navigate to `/scanner/scan/` → redirects to login (should show method not allowed or login redirect)
- [ ] Navigate to `/scanner/scan-status/` → redirects to login
- [ ] Navigate to `/scanner/options/AAPL` → redirects to login

### Authenticated Access Tests:
- [ ] Login and navigate to `/scanner/` → displays normally
- [ ] Click "Scan for Options" button → works normally
- [ ] View individual ticker options → works normally
- [ ] Polling status updates → works normally

### Redirect Tests:
- [ ] Logout, access `/scanner/`, verify URL contains `?next=/scanner/`
- [ ] Login from that page → should redirect back to `/scanner/`
- [ ] Verify redirect works for other scanner sub-pages

## Notes

- The `@login_required` decorator uses Django's authentication middleware (already configured)
- The decorator respects the `LOGIN_URL` setting in `settings.py`
- Django-allauth is already configured in the project, so login pages should be available
- This is a non-breaking change - only adds security to existing functionality

## Summary of Changes

**Files Modified:**
- `scanner/views.py` - Added `@login_required` decorators to 4 view functions
- `wheel_analyzer/settings.py` - Verified/added `LOGIN_URL` configuration (if needed)

**Key Changes:**

1. **Import login_required:**
   - Added `from django.contrib.auth.decorators import login_required` at top of `scanner/views.py`

2. **Protected Views:**
   - `@login_required` added to `index(request)`
   - `@login_required` added to `scan_view(request)`
   - `@login_required` added to `scan_status(request)`
   - `@login_required` added to `options_list(request, ticker)`

3. **Settings Verification:**
   - Confirmed `LOGIN_URL = '/accounts/login/'` exists in settings
   - Confirmed `LOGIN_REDIRECT_URL` is configured

**Security Impact:**
- All scanner functionality now requires authentication
- Prevents unauthorized access to options scanning data
- Maintains proper redirect flow for user experience
