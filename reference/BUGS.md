# Bugs

Pending:
- On /Users/danvigliotti/Development/Sirvig/wheel-analyzer/templates/scanner/partials/options_results.html line 35 - getting 'str' object has no attribute 'get'.  This is happening because the dictionary being passed is actually an empty string.  I think this is happening when the data in redis times out and nothing is returned.

Completed:
- ✅ Getting "Reverse for 'scan' not found. 'scan' is not a valid view function or pattern name." when clicking on "Options Scanner" button or navigating to /scanner/
  - **Fixed**: Added missing namespace prefix to URL template tags
  - **Files Changed**:
    - Modified: `templates/scanner/index.html` (changed `{% url 'scan' %}` to `{% url 'scanner:scan' %}`)
    - Modified: `templates/scanner/partials/scan_polling.html` (changed `{% url 'scan_status' %}` to `{% url 'scanner:scan_status' %}`)
  - **How it works**: The scanner app uses `app_name = "scanner"` in `scanner/urls.py`, creating a URL namespace. All URL references must include this namespace prefix (e.g., `scanner:scan` instead of just `scan`). Without the namespace, Django's URL reverser cannot find the matching pattern.
- ✅ The login and logout pages are not using any styling.  They should match the styling of the main site.
  - **Fixed**: Created custom allauth templates with Flowbite/Tailwind styling
  - **Files Changed**:
    - Created: `templates/account/base.html` (minimal layout with logo and "Return to Home" link)
    - Created: `templates/account/login.html` (styled login form with Flowbite components)
    - Created: `templates/account/logout.html` (styled logout confirmation)
  - **How it works**: Django-allauth uses template override system. Templates in `templates/account/` take priority over built-in allauth templates. Auth pages use minimal layout (no navbar) with centered forms, matching site's Flowbite/Tailwind aesthetic.
- ✅ When clicking the "Scan for Options" button, the last run is immediately placed in the status banner.  It should not display the last run information, it should display the current status of the scan.
  - **Fixed**: Set initial status in `scan_view()` before rendering template, removed problematic `elif` clause from template, added completion timestamp
  - **Files Changed**:
    - Modified: `scanner/views.py` (added initial status setting, completion message with timestamp)
    - Modified: `templates/scanner/partials/scan_polling.html` (simplified status logic, removed old error display)
  - **How it works**: When scan starts, `last_run` is immediately set to "Scanning in progress..." before template renders. Template logic simplified to show progress or default message. On completion, timestamp is added: "Scan completed successfully at [timestamp]"
- ✅ The scanner url should only be accessible by logged in users.  Currently any user can navigate to /scanner/
  - **Fixed**: Added `@login_required` decorators to all scanner views
  - **Files Changed**:
    - Modified: `scanner/views.py` (added decorators to 4 views)
    - Modified: `wheel_analyzer/settings.py` (added LOGIN_URL configuration)
  - **How it works**: Django's `@login_required` decorator checks authentication and redirects to `/accounts/login/?next=/scanner/` for unauthenticated users. After login, users are redirected back to the page they originally tried to access.
- ✅ The accordion expansion is not working on the scan_polling.html partial. The user should be able to expand the accordion tab to see the details.
  - **Fixed**: Created `static/js/app.js` with HTMX `afterSwap` event listener that calls Flowbite's `initFlowbite()` function
  - **Files Changed**: 
    - Created: `static/js/app.js`
    - Modified: `templates/base.html` (added script tag)
  - **How it works**: When HTMX swaps content (after clicking "Scan for Options"), Flowbite's `initFlowbite()` is called to reinitialize all components including accordions, restoring full click functionality