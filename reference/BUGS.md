# Bugs

Pending:
- The scanner url should only be accessible by logged in users.  Currently any user can navigate to /scanner/
- The login and logout pages are not using any styling.  They should match the styling of the main site.

Completed:
- ✅ The accordion expansion is not working on the scan_polling.html partial. The user should be able to expand the accordion tab to see the details.
  - **Fixed**: Created `static/js/app.js` with HTMX `afterSwap` event listener that calls Flowbite's `initFlowbite()` function
  - **Files Changed**: 
    - Created: `static/js/app.js`
    - Modified: `templates/base.html` (added script tag)
  - **How it works**: When HTMX swaps content (after clicking "Scan for Options"), Flowbite's `initFlowbite()` is called to reinitialize all components including accordions, restoring full click functionality