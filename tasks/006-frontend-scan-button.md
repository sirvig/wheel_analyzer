# Task 006: Implement Frontend Button for Manual Scan

## Progress Summary

**Status**: Completed

- [x] Step 1: Add Scan Button to Template
- [x] Step 2: Implement HTMX Interaction
- [x] Step 3: Add User Feedback Indicator

## Overview

This task involves updating the frontend of the scanner page to include a button that allows users to trigger a manual scan. The implementation will use HTMX to handle the user interaction, provide feedback during the scan, and update the results seamlessly.

## Implementation Steps

### Step 1: Add Scan Button to Template

- In the `scanner/index.html` template, add a `<button>` element with the text "Scan for Options".
- This button will be the primary user interface for triggering the manual scan.

**Files to modify:**

- `templates/scanner/index.html`

### Step 2: Implement HTMX Interaction

- Add HTMX attributes to the button to configure its behavior:
  - `hx-post`: Set this to the URL of the `scan_view` created in Task 005.
  - `hx-target`: Set this to the ID of the container `div` that wraps the options list.
  - `hx-swap`: Set to `innerHTML` to replace the content of the target container with the response from the server.
- Wrap the existing `{% include "scanner/options_list.html" %}` in a `div` with an ID that matches the `hx-target` attribute.

**Files to modify:**

- `templates/scanner/index.html`

### Step 3: Add User Feedback Indicator

- To provide immediate feedback to the user when the scan starts, use the `htmx-indicator` class.
- Add a `<span>` with this class inside the button to show a "Scanning..." message. The indicator will be automatically shown by HTMX during the request.
- The main button text can be wrapped in another `<span>` with the `htmx-non-indicator` class to be automatically hidden during the request.

**Files to modify:**

- `templates/scanner/index.html`

## Acceptance Criteria

- [x] A "Scan for Options" button is present on the scanner page.
- [x] Clicking the button sends a POST request to the correct backend view.
- [x] While the scan is running, a "Scanning..." indicator is visible to the user.
- [x] When the scan is complete, the options list on the page is updated with the new results without a full page reload.
- [x] If a scan is already in progress or if an error occurs, the message from the server is displayed correctly.

## Implementation Notes

- Added "Scan for Options" button to `templates/scanner/index.html`
- Button styled with Tailwind CSS classes matching the project theme (blue color scheme)
- HTMX attributes configured:
  - `hx-post="{% url 'scan' %}"` - Sends POST request to scan view
  - `hx-target="#scan-results"` - Targets the results container div
  - `hx-swap="innerHTML"` - Replaces container content with server response
- Implemented dual-state button text:
  - Normal state: "Scan for Options" with `htmx-non-indicator` class
  - Loading state: "Scanning..." with animated spinner icon and `htmx-indicator` class
- Added CSS rules to `static/css/styles.css` for HTMX indicator behavior:
  - `.htmx-indicator` hidden by default
  - `.htmx-request .htmx-indicator` shown during request
  - `.htmx-request .htmx-non-indicator` hidden during request
- Used Tailwind spinner SVG for loading animation
- Wrapped existing partial include in `#scan-results` div for HTMX targeting
- Button placement above scan results for clear user workflow
- No JavaScript required - all functionality handled by HTMX declaratively
