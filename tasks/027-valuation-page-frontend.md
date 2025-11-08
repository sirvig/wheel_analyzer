# Task 027: Create Curated Stock Valuation Page - Frontend

## Progress Summary

**Status**: Completed

- [x] Step 1: Create valuations.html template with table structure
- [x] Step 2: Add navigation dropdown to navbar (using Flowbite dropdown components)
- [ ] Step 3: Test page layout and responsive design (to be tested manually)
- [ ] Step 4: Verify NULL value handling (to be tested manually)

## Overview

Create the frontend template for the curated stock valuation page and add navigation in the navbar. This page displays a comprehensive table of all curated stocks with their intrinsic value calculations and assumptions.

The implementation adds:
- HTML template extending base.html with Bootstrap table
- Table columns for all key valuation data
- Proper formatting for currency, percentages, and dates
- Graceful handling of NULL values
- Navbar dropdown menu with links to scanner pages

## Current State Analysis

### Current Navbar Structure

The `templates/partials/navbar.html` currently has:
- Brand/logo link to home
- Individual navigation links (possibly: Home, Tracker, etc.)

**Missing**: Dropdown menu for Scanner-related pages

### Current Template Pattern

Other scanner templates extend `base.html`:
```django
{% extends "base.html" %}
{% load static %}

{% block content %}
  {# Page content here #}
{% endblock %}
```

### Available Context from Task 026

```python
context = {
    'stocks': QuerySet of CuratedStock instances
}
```

**Each stock has**:
- `symbol`, `name`, `is_active`
- `intrinsic_value`, `current_eps`, `eps_growth_rate`, `eps_multiple`
- `intrinsic_value_fcf`, `current_fcf_per_share`, `fcf_growth_rate`, `fcf_multiple`
- `preferred_valuation_method`, `desired_return`, `projection_years`
- `last_calculation_date`

## Target State

### Template Structure

**File**: `templates/scanner/valuations.html`

```django
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="container mt-4">
  <h1>Stock Valuations</h1>
  <p class="text-muted">
    Intrinsic value calculations for {{ stocks.count }} active curated stocks
  </p>
  
  {% if stocks %}
    <div class="table-responsive">
      <table class="table table-striped table-hover">
        {# Table content #}
      </table>
    </div>
  {% else %}
    <div class="alert alert-info">
      No active curated stocks found.
    </div>
  {% endif %}
</div>
{% endblock %}
```

### Table Columns

1. **Ticker** - Stock symbol
2. **Company** - Company name
3. **IV (EPS)** - EPS-based intrinsic value
4. **IV (FCF)** - FCF-based intrinsic value
5. **Preferred** - Preferred valuation method (EPS/FCF)
6. **Last Calc** - Last calculation date
7. **Assumptions** - Key assumptions (growth rates, multiples)

### Navbar Dropdown

```html
<li class="nav-item dropdown">
  <a class="nav-link dropdown-toggle" href="#" id="scannerDropdown" 
     role="button" data-bs-toggle="dropdown" aria-expanded="false">
    Scanner
  </a>
  <ul class="dropdown-menu" aria-labelledby="scannerDropdown">
    <li><a class="dropdown-item" href="{% url 'scanner:index' %}">Options Scanner</a></li>
    <li><a class="dropdown-item" href="{% url 'scanner:valuations' %}">Stock Valuations</a></li>
  </ul>
</li>
```

## Implementation Steps

### Step 1: Create valuations.html template with table structure

Create the template file with table displaying all valuation data.

**File to create**: `templates/scanner/valuations.html`

**Full template content**:

```django
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="container mt-4">
  {# Page header #}
  <div class="d-flex justify-content-between align-items-center mb-4">
    <div>
      <h1>Stock Valuations</h1>
      <p class="text-muted mb-0">
        Intrinsic value calculations for {{ stocks.count }} active curated stock{{ stocks.count|pluralize }}
      </p>
    </div>
  </div>
  
  {# Valuation table #}
  {% if stocks %}
    <div class="table-responsive">
      <table class="table table-striped table-hover align-middle">
        <thead class="table-dark">
          <tr>
            <th>Ticker</th>
            <th>Company</th>
            <th>IV (EPS)</th>
            <th>IV (FCF)</th>
            <th>Preferred</th>
            <th>Last Calc</th>
            <th>Assumptions</th>
          </tr>
        </thead>
        <tbody>
          {% for stock in stocks %}
            <tr>
              {# Ticker #}
              <td>
                <strong>{{ stock.symbol }}</strong>
              </td>
              
              {# Company name #}
              <td>{{ stock.name }}</td>
              
              {# EPS intrinsic value #}
              <td>
                {% if stock.intrinsic_value %}
                  ${{ stock.intrinsic_value|floatformat:2 }}
                {% else %}
                  <span class="text-muted">-</span>
                {% endif %}
              </td>
              
              {# FCF intrinsic value #}
              <td>
                {% if stock.intrinsic_value_fcf %}
                  ${{ stock.intrinsic_value_fcf|floatformat:2 }}
                {% else %}
                  <span class="text-muted">-</span>
                {% endif %}
              </td>
              
              {# Preferred method #}
              <td>
                {% if stock.preferred_valuation_method == 'eps' %}
                  <span class="badge bg-primary">EPS</span>
                {% elif stock.preferred_valuation_method == 'fcf' %}
                  <span class="badge bg-info">FCF</span>
                {% else %}
                  <span class="text-muted">-</span>
                {% endif %}
              </td>
              
              {# Last calculation date #}
              <td>
                {% if stock.last_calculation_date %}
                  {{ stock.last_calculation_date|date:"M d, Y" }}
                  <br>
                  <small class="text-muted">{{ stock.last_calculation_date|date:"g:i A" }}</small>
                {% else %}
                  <span class="text-muted">Never</span>
                {% endif %}
              </td>
              
              {# Assumptions #}
              <td>
                <small>
                  {% if stock.preferred_valuation_method == 'eps' %}
                    Growth: {{ stock.eps_growth_rate|floatformat:0 }}%<br>
                    Multiple: {{ stock.eps_multiple|floatformat:0 }}<br>
                  {% elif stock.preferred_valuation_method == 'fcf' %}
                    Growth: {{ stock.fcf_growth_rate|floatformat:0 }}%<br>
                    Multiple: {{ stock.fcf_multiple|floatformat:0 }}<br>
                  {% else %}
                    <span class="text-muted">-</span>
                  {% endif %}
                  Return: {{ stock.desired_return|floatformat:0 }}%
                </small>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    {# No stocks found #}
    <div class="alert alert-info" role="alert">
      <h4 class="alert-heading">No Active Stocks</h4>
      <p>No active curated stocks found. Add stocks via the Django admin interface.</p>
    </div>
  {% endif %}
</div>
{% endblock %}
```

**Key features**:
- Bootstrap table classes: `table-striped table-hover align-middle`
- Dark header: `table-dark`
- Responsive wrapper: `table-responsive`
- NULL value handling with fallback to "-"
- Date formatting with `date` filter
- Currency formatting with `floatformat:2`
- Percentage formatting with `floatformat:0`
- Badges for preferred method
- Small text for assumptions

### Step 2: Add navigation dropdown to navbar

Update the navbar to include a Scanner dropdown menu.

**File to modify**: `templates/partials/navbar.html`

**Current navbar structure** (example, adjust as needed):
```html
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="{% url 'index' %}">Wheel Analyzer</a>
    
    <button class="navbar-toggler" ...>
      <span class="navbar-toggler-icon"></span>
    </button>
    
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item">
          <a class="nav-link" href="{% url 'index' %}">Home</a>
        </li>
        {# Add Scanner dropdown here #}
      </ul>
    </div>
  </div>
</nav>
```

**Add Scanner dropdown** (insert in navbar-nav list):

```html
<li class="nav-item dropdown">
  <a class="nav-link dropdown-toggle" href="#" id="scannerDropdown" 
     role="button" data-bs-toggle="dropdown" aria-expanded="false">
    Scanner
  </a>
  <ul class="dropdown-menu" aria-labelledby="scannerDropdown">
    <li>
      <a class="dropdown-item" href="{% url 'scanner:index' %}">
        Options Scanner
      </a>
    </li>
    <li>
      <a class="dropdown-item" href="{% url 'scanner:valuations' %}">
        Stock Valuations
      </a>
    </li>
  </ul>
</li>
```

**Location**: Add after existing nav items, before user/auth links

**If existing scanner link**: Replace single "Scanner" link with dropdown

### Step 3: Test page layout and responsive design

Verify the page displays correctly on different screen sizes.

**Manual testing checklist**:

1. **Desktop view (>992px)**:
   - [ ] Navigate to `/scanner/valuations/`
   - [ ] Table displays all 7 columns clearly
   - [ ] No horizontal scrolling needed
   - [ ] Navbar dropdown works correctly
   - [ ] Hover effects work on table rows

2. **Tablet view (768px - 991px)**:
   - [ ] Table uses horizontal scroll in responsive wrapper
   - [ ] Navbar collapses to hamburger menu
   - [ ] Dropdown still works in collapsed navbar
   - [ ] Content readable without zoom

3. **Mobile view (<768px)**:
   - [ ] Table scrolls horizontally (expected behavior)
   - [ ] Navbar hamburger menu works
   - [ ] Text remains readable
   - [ ] Touch targets are adequate size

**Browser testing**:
- Chrome (primary)
- Firefox
- Safari (if on Mac)
- Mobile browsers (Chrome/Safari on phone)

**Test data scenarios**:

1. **Full data set**:
   - All stocks have both EPS and FCF values
   - All stocks have recent calculation dates
   - Verify formatting looks good

2. **Partial data**:
   - Some stocks with NULL EPS or FCF values
   - Some stocks never calculated (NULL date)
   - Verify "-" appears correctly
   - Verify "Never" appears for NULL dates

3. **Empty data**:
   - Set all stocks to `is_active=False`
   - Verify "No active stocks" message appears

**Visual inspection**:
- Alignment of currency values (right-aligned would be nice, but not required)
- Date formatting is consistent
- Badges for preferred method are clear
- Table header is visually distinct
- Striped rows enhance readability

### Step 4: Verify NULL value handling

Test that NULL values display gracefully without errors.

**Test setup** (Django shell):

```bash
just exec python manage.py shell
```

```python
from scanner.models import CuratedStock

# Create test stock with NULL values
stock = CuratedStock.objects.filter(is_active=True).first()

# Set all intrinsic values to NULL
stock.intrinsic_value = None
stock.intrinsic_value_fcf = None
stock.last_calculation_date = None
stock.save()

print(f"Test stock: {stock.symbol}")
print(f"EPS IV: {stock.intrinsic_value}")
print(f"FCF IV: {stock.intrinsic_value_fcf}")
print(f"Last calc: {stock.last_calculation_date}")
```

**Then visit page**:
1. Navigate to `/scanner/valuations/`
2. Find the test stock in the table
3. Verify columns show:
   - IV (EPS): "-" (gray text)
   - IV (FCF): "-" (gray text)
   - Last Calc: "Never" (gray text)
   - Assumptions: Show values (growth rates still exist)

**Template filter testing**:

Test Django template filters handle NULL correctly:
- `{{ None|floatformat:2 }}` → Empty string (Django default)
- `{% if None %}` → False (expected)
- `{{ None|date:"M d, Y" }}` → Empty string (expected)

**Error checking**:
- No 500 errors on page load
- No template syntax errors in logs
- No JavaScript console errors

**Restore test data**:
```python
# In Django shell
stock.intrinsic_value = 150.00
stock.intrinsic_value_fcf = 148.00
stock.last_calculation_date = timezone.now()
stock.save()
```

## Acceptance Criteria

### Template Requirements

- [ ] Template file created at `templates/scanner/valuations.html`
- [ ] Template extends `base.html`
- [ ] Page title is "Stock Valuations"
- [ ] Table has 7 columns as specified
- [ ] Bootstrap table classes applied correctly
- [ ] Table wrapped in `table-responsive` div

### Data Display Requirements

- [ ] All active stocks displayed in table
- [ ] Ticker symbols displayed as bold
- [ ] Company names displayed
- [ ] Currency values formatted with 2 decimal places
- [ ] Percentages formatted as whole numbers
- [ ] Dates formatted as "Mon DD, YYYY"
- [ ] Time shown below date in smaller text

### NULL Handling Requirements

- [ ] NULL intrinsic values show "-" in gray
- [ ] NULL calculation date shows "Never"
- [ ] NULL preferred method shows "-"
- [ ] No template errors with NULL values
- [ ] Empty stock list shows appropriate message

### Navigation Requirements

- [ ] Scanner dropdown added to navbar
- [ ] Dropdown contains "Options Scanner" link
- [ ] Dropdown contains "Stock Valuations" link
- [ ] Links use correct URL names
- [ ] Dropdown works on desktop
- [ ] Dropdown works in mobile collapsed menu
- [ ] Active page highlighted (optional enhancement)

### Responsive Design Requirements

- [ ] Table is responsive on mobile (<768px)
- [ ] Horizontal scroll works when needed
- [ ] Navbar collapses on mobile
- [ ] Content readable without zoom
- [ ] No layout breaking on any screen size

### Visual/UX Requirements

- [ ] Table is visually clear and readable
- [ ] Striped rows enhance readability
- [ ] Hover effects work on rows
- [ ] Header is visually distinct
- [ ] Badges for preferred method are clear
- [ ] Spacing and padding are appropriate

## Files Involved

### New Files

- `templates/scanner/valuations.html` - Main template for valuation page

### Modified Files

- `templates/partials/navbar.html` - Add Scanner dropdown menu

## Notes

### Bootstrap Table Classes

**Main classes**:
- `table` - Base table styles
- `table-striped` - Alternating row colors
- `table-hover` - Row highlight on hover
- `align-middle` - Vertical align cell content

**Header styling**:
- `table-dark` - Dark background for header
- Alternative: `table-light` for light header

**Responsive**:
- `table-responsive` - Horizontal scroll on small screens
- Breakpoint variants: `table-responsive-sm`, `table-responsive-md`

### Django Template Filters

**Number formatting**:
- `{{ value|floatformat:2 }}` - 2 decimal places (e.g., "150.25")
- `{{ value|floatformat:0 }}` - Whole number (e.g., "10")

**Date formatting**:
- `{{ date|date:"M d, Y" }}` - "Jan 15, 2025"
- `{{ date|date:"g:i A" }}` - "2:30 PM"

**Pluralization**:
- `{{ count }} stock{{ count|pluralize }}` - "1 stock" or "2 stocks"

### Badge Color Choices

**Preferred method badges**:
- EPS: `bg-primary` (blue) - Primary valuation method
- FCF: `bg-info` (light blue) - Alternative method

**Could also use**:
- `bg-success` (green)
- `bg-secondary` (gray)
- Custom colors in CSS

### Assumptions Column

**Display logic**:
Shows assumptions for the preferred method only:
- If EPS preferred: EPS growth rate, EPS multiple
- If FCF preferred: FCF growth rate, FCF multiple
- Always show: Desired return (applies to both)

**Format**:
```
Growth: 10%
Multiple: 20
Return: 15%
```

**Uses `<small>` tag** for compact display

### Future Enhancements (Not This Task)

**Possible additions**:
- Sort table by clicking column headers
- Search/filter by ticker or name
- Toggle between showing all assumptions or just preferred
- Export table to CSV
- Display current stock price for comparison
- Show discount/premium percentage (price vs IV)

**Current scope**: Simple static table

### Accessibility

**Table accessibility**:
- Header row uses `<thead>` and `<th>` tags
- Proper table structure for screen readers
- Text alternatives for badges (badge text is readable)

**Navbar accessibility**:
- Dropdown uses proper ARIA attributes
- `role="button"` on dropdown toggle
- `aria-expanded` for dropdown state
- `aria-labelledby` on dropdown menu

### Performance

**Template rendering**:
- Simple table iteration: O(n) where n = number of stocks
- No database queries in template (all data in context)
- Typical: 26 stocks = ~20ms render time

**Page load**:
- Full page: ~50-100ms total
- No AJAX/JavaScript needed
- Static content after initial load

## Dependencies

- Requires Task 026 (backend view and URL)
- Uses `CuratedStock` model from Phase 4
- Requires Bootstrap 5 (already in project)
- Extends `base.html` template

## Reference

**Bootstrap Tables**:
- https://getbootstrap.com/docs/5.0/content/tables/

**Bootstrap Dropdowns**:
- https://getbootstrap.com/docs/5.0/components/dropdowns/

**Django Template Language**:
- Filters: https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#built-in-filter-reference
- Date formatting: https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#date

**Responsive Design**:
- Bootstrap breakpoints: https://getbootstrap.com/docs/5.0/layout/breakpoints/
