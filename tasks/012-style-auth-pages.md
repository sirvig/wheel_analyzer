# Task 012: Style Authentication Pages

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Create account template directory structure
- [x] Step 2: Create minimal base template for auth pages
- [x] Step 3: Create styled login page
- [x] Step 4: Create styled logout page
- [ ] Step 5: Verify and test authentication flow (manual testing required)

## Overview

This task fixes a bug where django-allauth's default login and logout pages lack styling and don't match the site's design. We'll create custom templates that override allauth's defaults, using Flowbite/Tailwind components to match the main site's aesthetic. The auth pages will use a minimal layout (no navbar, just logo and "Return to Home" link).

**Related Bug:** Reference BUGS.md - "The login and logout pages are not using any styling. They should match the styling of the main site."

## Implementation Steps

### Step 1: Create account template directory structure

- Create `templates/account/` directory
- This directory will contain allauth template overrides
- Django's template system will prioritize these over allauth's built-in templates

**Directories to create:**
```
templates/
  account/
    (templates will be created here)
```

**Command:**
```bash
mkdir -p templates/account
```

### Step 2: Create minimal base template for auth pages

- Create `templates/account/base.html`
- Include same CSS/JS as main site (Tailwind, Flowbite, DaisyUI, HTMX)
- Create minimal layout structure:
  - Logo/site name centered at top
  - "Return to Home" link
  - Content block for forms
  - NO navbar (different from main `base.html`)

**Files to create:**
- `templates/account/base.html`

**Template structure:**
```django
<!DOCTYPE html>
<html lang="en">
<head>
    {# Same CSS/JS includes as main base.html #}
    {# Tailwind, Flowbite, DaisyUI #}
</head>
<body>
    <div class="min-h-screen flex flex-col items-center justify-center bg-gray-50">
        {# Logo/site name #}
        {# Return to Home link #}
        
        <div class="w-full max-w-md">
            {% block content %}
            {% endblock %}
        </div>
    </div>
    {# Flowbite JS #}
</body>
</html>
```

### Step 3: Create styled login page

- Create `templates/account/login.html`
- Override allauth's default `account/login.html` template
- Extend `account/base.html`
- Use Flowbite form components for styling:
  - Card container for the form
  - Styled input fields (username/email, password)
  - Styled "Remember me" checkbox
  - Styled submit button
  - "Forgot password?" link (if applicable)
  - "Don't have an account? Sign up" link (if applicable)
- Center form vertically and horizontally

**Files to create:**
- `templates/account/login.html`

**Form components to style:**
- Email/username input field
- Password input field
- "Remember me" checkbox
- "Login" submit button
- Links (forgot password, sign up)
- Error messages display

**Flowbite components to use:**
- Form card: `class="bg-white rounded-lg shadow-md p-6"`
- Input fields: Flowbite text input styles
- Buttons: Flowbite primary button styles
- Links: Flowbite link styles

### Step 4: Create styled logout page

- Create `templates/account/logout.html`
- Override allauth's default `account/logout.html` template
- Extend `account/base.html`
- Style the logout confirmation:
  - Card container for confirmation message
  - "Are you sure you want to log out?" message
  - Styled "Confirm Logout" button (form submission)
  - Styled "Cancel" button/link (returns to previous page)
- Center content vertically and horizontally

**Files to create:**
- `templates/account/logout.html`

**Components to style:**
- Confirmation message
- "Sign Out" form button (primary/danger style)
- "Cancel" link (secondary style)
- Success message display (if logout is immediate)

### Step 5: Verify and test authentication flow

- Verify `settings.py` configuration:
  - `TEMPLATES['DIRS']` includes `BASE_DIR / "templates"` (already correct)
  - Check `ACCOUNT_*` settings for any needed customizations
- Test login page rendering and functionality
- Test logout page rendering and functionality
- Test responsive design on mobile/tablet
- Verify forms work correctly (validation, error display, success)

**Files to check:**
- `wheel_analyzer/settings.py`

## Acceptance Criteria

- [ ] Login page uses Flowbite/Tailwind styling matching site aesthetic
- [ ] Logout page uses Flowbite/Tailwind styling matching site aesthetic
- [ ] Both pages have minimal layout (logo + "Return to Home" link, NO navbar)
- [ ] Forms are centered and visually appealing
- [ ] All form elements are properly styled (inputs, buttons, checkboxes, links)
- [ ] Error messages display with appropriate styling
- [ ] Forms are fully functional (login works, logout works)
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] "Return to Home" link navigates to correct page

## Testing Checklist

### Visual/Styling Tests:
- [ ] Navigate to `/accounts/login/` → verify Flowbite styling applied
- [ ] Check logo displays correctly at top
- [ ] Check "Return to Home" link is visible and styled
- [ ] Verify NO navbar is present
- [ ] Check form is centered on page
- [ ] Verify input fields use Flowbite styling
- [ ] Check buttons use Flowbite styling
- [ ] Test responsive design on mobile viewport

### Functional Tests:
- [ ] Click "Return to Home" link → navigates to home page
- [ ] Enter invalid credentials → error message displays with styling
- [ ] Enter valid credentials → successfully logs in
- [ ] After login, redirects to appropriate page
- [ ] Navigate to `/accounts/logout/` → confirmation page displays
- [ ] Click "Cancel" → returns to previous page without logging out
- [ ] Click "Sign Out" → successfully logs out
- [ ] After logout, redirects to appropriate page

### Cross-browser Tests:
- [ ] Test in Chrome
- [ ] Test in Firefox
- [ ] Test in Safari
- [ ] Test on mobile device (iOS/Android)

### Accessibility Tests:
- [ ] Tab navigation works correctly through form fields
- [ ] Form labels are properly associated with inputs
- [ ] Error messages are accessible
- [ ] Buttons are keyboard accessible

## Notes

- Django-allauth looks for templates in `templates/account/` directory
- Template override priority: project templates > allauth templates
- The `base.html` for auth pages is separate from main site's `base.html`
- Allauth forms are available as template context (e.g., `{{ form }}`)
- Use `widget_tweaks` (already installed) to add CSS classes to form fields
- Flowbite form components: https://flowbite.com/docs/components/forms/
- DaisyUI is also available if preferred for certain components

## Reference

**Allauth template names:**
- `account/login.html` - Login page
- `account/logout.html` - Logout confirmation page
- `account/signup.html` - Registration page (if needed later)
- `account/password_reset.html` - Password reset (if needed later)

**Flowbite component references:**
- Forms: https://flowbite.com/docs/components/forms/
- Cards: https://flowbite.com/docs/components/card/
- Buttons: https://flowbite.com/docs/components/buttons/

**Current site styling:**
- Main site uses: Tailwind CSS, Flowbite, DaisyUI
- Color scheme: Blue accents (see scan status banner)
- Typography: Default Tailwind font stack

## Summary of Changes

**Files Created:**
- `templates/account/base.html` - Minimal base template for auth pages
- `templates/account/login.html` - Styled login page
- `templates/account/logout.html` - Styled logout confirmation page

**Key Changes:**

1. **account/base.html:**
   - Minimal layout without navbar
   - Logo/site name centered at top
   - "Return to Home" link prominently displayed
   - Includes all necessary CSS/JS (Tailwind, Flowbite, DaisyUI)
   - Content block for form templates
   - Flexbox centering for vertical/horizontal alignment

2. **account/login.html:**
   - Extends `account/base.html`
   - Uses Flowbite card component for form container
   - Styled form fields using Flowbite input components
   - Styled "Remember me" checkbox
   - Styled "Login" button (Flowbite primary button)
   - Styled error message display
   - Links for "Forgot password?" and "Sign up"

3. **account/logout.html:**
   - Extends `account/base.html`
   - Uses Flowbite card component for confirmation
   - Clear "Are you sure?" message
   - Styled "Sign Out" button (Flowbite danger/primary button)
   - Styled "Cancel" link (Flowbite secondary button style)
   - Proper form handling for logout action

**User Experience:**
- Clean, minimal auth pages matching site aesthetic
- Easy navigation back to main site via "Return to Home" link
- Professional appearance builds trust
- Consistent styling throughout authentication flow
- Mobile-friendly responsive design
