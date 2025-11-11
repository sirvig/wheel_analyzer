# Task 040: Comparison Report Frontend Template

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create valuation_comparison.html template
- [ ] Step 2: Add comparison table with deltas
- [ ] Step 3: Add color-coding for positive/negative changes
- [ ] Step 4: Add navigation and export links
- [ ] Step 5: Test responsive design
- [ ] Step 6: Manual UI testing

## Overview

Create a frontend template for the valuation comparison report that displays current vs. historical intrinsic values side-by-side with visual indicators for changes. The table will use color-coding (green for increases, red for decreases) to make trends immediately visible to users.

**Current State**:
- Backend view exists (Task 039)
- No template to display comparison data
- Users cannot see valuation changes

**Target State**:
- Template at `scanner/templates/scanner/valuation_comparison.html`
- Responsive table with 7 columns per comparison period
- Color-coded deltas (green=positive, red=negative, gray=neutral/null)
- Current, previous quarter, and year-ago columns
- Navigation links and CSV export button
- Mobile-friendly with horizontal scroll

## High-Level Specifications

### Template Structure

```
Header
  - Title: "Valuation Comparison Report"
  - Comparison date badges (quarter, year)
  - Export All CSV button

Comparison Table
  - Stock column (ticker + name)
  - Current Value column
  - Previous Quarter columns (value, delta $, delta %)
  - Year Ago columns (value, delta $, delta %)
  - Color-coded cells based on delta sign

Empty State (if no stocks)
  - Info message about no data
```

### Color Coding

- **Positive changes (increases)**: Green text (`text-green-600`)
- **Negative changes (decreases)**: Red text (`text-red-600`)
- **Zero or NULL**: Gray text (`text-gray-500`)
- **Delta format**: `+$10.00 (+7.14%)` or `-$5.00 (-3.33%)`

## Relevant Files

### Files to Create
- `scanner/templates/scanner/valuation_comparison.html` - Main template file

### Files to Modify
- `scanner/templates/scanner/valuations.html` - Add "Comparison Report" link in navigation (optional)

### Files for Testing
- Manual testing via browser (no automated template tests)

## Acceptance Criteria

### Template Requirements
- [ ] Template extends `base.html`
- [ ] Title block set to "Valuation Comparison Report"
- [ ] Content block contains all UI elements
- [ ] Uses Tailwind CSS utility classes
- [ ] No inline styles

### Header Requirements
- [ ] H1 displays "Valuation Comparison Report"
- [ ] Date badges show comparison periods
- [ ] Export All CSV button with download icon
- [ ] Back to Valuations button

### Comparison Table
- [ ] Table shows all required columns
- [ ] Stock ticker and name displayed
- [ ] Current values formatted with $
- [ ] Delta values formatted with +/- sign
- [ ] Percentage values formatted with %
- [ ] NULL values show as "-"
- [ ] Color coding applied to delta cells
- [ ] Responsive with horizontal scroll wrapper

### Color Coding
- [ ] Positive deltas use `text-green-600`
- [ ] Negative deltas use `text-red-600`
- [ ] Zero/NULL deltas use `text-gray-500`
- [ ] Colors consistent across all delta columns
- [ ] Font weight for deltas (`font-semibold`)

### Navigation
- [ ] Export All CSV button links to export view (Task 041)
- [ ] Back to Valuations button functional
- [ ] Both buttons styled consistently

### Responsive Design
- [ ] Desktop: Full table visible
- [ ] Tablet: Table scrolls horizontally if needed
- [ ] Mobile: Table scrolls horizontally
- [ ] No overflow or layout breaks

## Implementation Steps

### Step 1: Create valuation_comparison.html template

Create the base template structure.

**File to create**: `scanner/templates/scanner/valuation_comparison.html`

**Content**:
```django
{% extends "base.html" %}
{% load static %}

{% block title %}Valuation Comparison Report{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-6">
    <!-- Header -->
    <div class="mb-6">
        <div class="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
            <div>
                <h1 class="text-3xl font-bold text-gray-900">Valuation Comparison Report</h1>
                <p class="text-gray-600 mt-1">
                    Compare current intrinsic values to historical snapshots
                </p>
                <div class="flex gap-2 mt-3">
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Previous Quarter: {{ comparison_date_quarter|date:"M d, Y" }}
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        Year Ago: {{ comparison_date_year|date:"M d, Y" }}
                    </span>
                </div>
            </div>
            <div class="flex gap-3">
                <a href="{% url 'scanner:export_all_history' %}"
                   class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                    Export All CSV
                </a>
                <a href="{% url 'scanner:valuations' %}"
                   class="inline-flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
                    </svg>
                    Back to Valuations
                </a>
            </div>
        </div>
    </div>

    {% if stocks %}
        <!-- Comparison Table -->
        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <!-- Stock Info -->
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                                Stock
                            </th>
                            <!-- Current Value -->
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                                Current Value
                            </th>
                            <!-- Previous Quarter -->
                            <th colspan="3" class="px-6 py-3 text-center text-xs font-medium text-blue-600 uppercase tracking-wider border-l-2 border-blue-200">
                                Previous Quarter
                            </th>
                            <!-- Year Ago -->
                            <th colspan="3" class="px-6 py-3 text-center text-xs font-medium text-purple-600 uppercase tracking-wider border-l-2 border-purple-200">
                                Year Ago
                            </th>
                        </tr>
                        <tr>
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase"></th>
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase"></th>
                            <!-- Quarter subheaders -->
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase border-l-2 border-blue-200">Value</th>
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase">Change $</th>
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase">Change %</th>
                            <!-- Year subheaders -->
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase border-l-2 border-purple-200">Value</th>
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase">Change $</th>
                            <th class="px-6 py-2 text-left text-xs font-medium text-gray-500 uppercase">Change %</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {% for item in stocks %}
                        <tr class="hover:bg-gray-50 transition">
                            <!-- Stock -->
                            <td class="px-6 py-4 whitespace-nowrap">
                                <div class="flex flex-col">
                                    <span class="text-sm font-medium text-gray-900">{{ item.stock.symbol }}</span>
                                    <span class="text-xs text-gray-500">{{ item.stock.name|truncatewords:3 }}</span>
                                </div>
                            </td>

                            <!-- Current Value -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                                {% if item.current_value %}${{ item.current_value }}{% else %}-{% endif %}
                            </td>

                            <!-- Previous Quarter: Value -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 border-l-2 border-blue-100">
                                {% if item.quarter_value %}${{ item.quarter_value }}{% else %}-{% endif %}
                            </td>

                            <!-- Previous Quarter: Delta $ -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold
                                {% if item.quarter_delta > 0 %}text-green-600
                                {% elif item.quarter_delta < 0 %}text-red-600
                                {% else %}text-gray-500{% endif %}">
                                {% if item.quarter_delta is not None %}
                                    {% if item.quarter_delta > 0 %}+{% endif %}${{ item.quarter_delta }}
                                {% else %}-{% endif %}
                            </td>

                            <!-- Previous Quarter: Delta % -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold
                                {% if item.quarter_pct > 0 %}text-green-600
                                {% elif item.quarter_pct < 0 %}text-red-600
                                {% else %}text-gray-500{% endif %}">
                                {% if item.quarter_pct is not None %}
                                    {% if item.quarter_pct > 0 %}+{% endif %}{{ item.quarter_pct|floatformat:2 }}%
                                {% else %}-{% endif %}
                            </td>

                            <!-- Year Ago: Value -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 border-l-2 border-purple-100">
                                {% if item.year_value %}${{ item.year_value }}{% else %}-{% endif %}
                            </td>

                            <!-- Year Ago: Delta $ -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold
                                {% if item.year_delta > 0 %}text-green-600
                                {% elif item.year_delta < 0 %}text-red-600
                                {% else %}text-gray-500{% endif %}">
                                {% if item.year_delta is not None %}
                                    {% if item.year_delta > 0 %}+{% endif %}${{ item.year_delta }}
                                {% else %}-{% endif %}
                            </td>

                            <!-- Year Ago: Delta % -->
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold
                                {% if item.year_pct > 0 %}text-green-600
                                {% elif item.year_pct < 0 %}text-red-600
                                {% else %}text-gray-500{% endif %}">
                                {% if item.year_pct is not None %}
                                    {% if item.year_pct > 0 %}+{% endif %}{{ item.year_pct|floatformat:2 }}%
                                {% else %}-{% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Legend -->
        <div class="mt-4 flex justify-center gap-6 text-sm">
            <div class="flex items-center gap-2">
                <div class="w-3 h-3 bg-green-600 rounded"></div>
                <span class="text-gray-600">Increased</span>
            </div>
            <div class="flex items-center gap-2">
                <div class="w-3 h-3 bg-red-600 rounded"></div>
                <span class="text-gray-600">Decreased</span>
            </div>
            <div class="flex items-center gap-2">
                <div class="w-3 h-3 bg-gray-400 rounded"></div>
                <span class="text-gray-600">No Change / No Data</span>
            </div>
        </div>
    {% else %}
        <!-- No Stocks Message -->
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <div class="flex items-start">
                <svg class="w-6 h-6 text-yellow-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-yellow-800">No Stocks Available</h3>
                    <p class="mt-2 text-sm text-yellow-700">
                        No active curated stocks found. Add stocks via the Django admin interface to see comparison data.
                    </p>
                </div>
            </div>
        </div>
    {% endif %}
</div>
{% endblock %}
```

**Verify template syntax**:
```bash
uv run python manage.py check --deploy
```

### Step 2: Add comparison table with deltas

The table is already included in Step 1. Verify it renders correctly.

**Test with sample data**:
```bash
# Start server
just run

# Login and navigate to:
http://localhost:8000/scanner/valuations/comparison/
```

**Verify table**:
- All 8 columns visible
- Stock ticker and name display
- Current value displays
- Quarter and year columns separated visually
- Borders distinguish comparison periods

### Step 3: Add color-coding for positive/negative changes

Color coding is already included in Step 1 via conditional CSS classes.

**Verify color logic**:

The template uses Django template conditionals:
```django
{% if item.quarter_delta > 0 %}text-green-600
{% elif item.quarter_delta < 0 %}text-red-600
{% else %}text-gray-500{% endif %}
```

**Test scenarios**:
1. **Positive change**: Create stock with current > historical
   - Expected: Green text for delta
2. **Negative change**: Create stock with current < historical
   - Expected: Red text for delta
3. **Zero change**: Create stock with current = historical
   - Expected: Gray text for delta
4. **NULL**: Stock with no historical snapshot
   - Expected: Gray "-" displayed

**Manual test**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal

>>> # Create stock with positive change
>>> stock_up = CuratedStock.objects.create(
...     symbol="TESTUP",
...     active=True,
...     intrinsic_value=Decimal("150.00"),
...     preferred_valuation_method="EPS"
... )
>>> ValuationHistory.objects.create(
...     stock=stock_up,
...     snapshot_date=date(2024, 10, 1),
...     intrinsic_value=Decimal("140.00"),
...     preferred_valuation_method="EPS",
...     eps_growth_rate=Decimal("10.0"),
...     eps_multiple=Decimal("20.0"),
...     fcf_growth_rate=Decimal("10.0"),
...     fcf_multiple=Decimal("20.0"),
...     desired_return=Decimal("15.0"),
...     projection_years=5,
... )

>>> # Create stock with negative change
>>> stock_down = CuratedStock.objects.create(
...     symbol="TESTDOWN",
...     active=True,
...     intrinsic_value=Decimal("130.00"),
...     preferred_valuation_method="EPS"
... )
>>> ValuationHistory.objects.create(
...     stock=stock_down,
...     snapshot_date=date(2024, 10, 1),
...     intrinsic_value=Decimal("140.00"),
...     preferred_valuation_method="EPS",
...     eps_growth_rate=Decimal("10.0"),
...     eps_multiple=Decimal("20.0"),
...     fcf_growth_rate=Decimal("10.0"),
...     fcf_multiple=Decimal("20.0"),
...     desired_return=Decimal("15.0"),
...     projection_years=5,
... )

>>> exit()
```

**View in browser**:
- TESTUP row should show green deltas (positive)
- TESTDOWN row should show red deltas (negative)

**Cleanup**:
```bash
uv run python manage.py shell
>>> from scanner.models import CuratedStock
>>> CuratedStock.objects.filter(symbol__startswith="TEST").delete()
>>> exit()
```

### Step 4: Add navigation and export links

Navigation links already included in Step 1.

**Verify links**:
- Export All CSV button: links to `scanner:export_all_history` (Task 041)
- Back to Valuations button: links to `scanner:valuations`

**Note**: Export button will 404 until Task 041 is completed.

**Test Back button**:
1. Navigate to comparison report
2. Click "Back to Valuations"
3. Should navigate to `/scanner/valuations/`

### Step 5: Test responsive design

Test layout on different screen sizes.

**Desktop testing** (≥1024px):
```
Browser DevTools → 1200px width
```

**Verify**:
- Full table visible without scroll
- All 8 columns readable
- Color coding visible
- Buttons side by side

**Tablet testing** (768-1023px):
```
Browser DevTools → 800px width
```

**Verify**:
- Table may require horizontal scroll (acceptable)
- Header elements adjust layout
- Date badges wrap if needed

**Mobile testing** (<768px):
```
Browser DevTools → iPhone SE (375px width)
```

**Verify**:
- Table scrolls horizontally (expected)
- Header elements stack vertically
- Buttons stack vertically
- Text readable without zooming
- Legend visible and readable

### Step 6: Manual UI testing

Comprehensive manual testing of all features.

**Test Checklist**:
```
[ ] Page loads without errors
[ ] Title and description display correctly
[ ] Comparison date badges show correct dates
[ ] Table renders with all columns
[ ] Stock ticker and names display
[ ] Current values formatted with $
[ ] Quarter comparison values formatted correctly
[ ] Year comparison values formatted correctly
[ ] Positive deltas show in green
[ ] Negative deltas show in red
[ ] Zero/NULL deltas show in gray
[ ] +/- signs display on deltas
[ ] Percentage values formatted with %
[ ] NULL values show as "-"
[ ] Hover effect on table rows
[ ] Export All CSV button present (may 404 until Task 041)
[ ] Back to Valuations button works
[ ] Legend displays at bottom
[ ] No JavaScript console errors
[ ] No layout overflow on any device
[ ] Colors meet accessibility contrast standards
```

**Test with various data**:
- Many stocks (20+)
- Few stocks (1-3)
- Stocks with all positive changes
- Stocks with all negative changes
- Stocks with mixed changes
- Stocks with NULL current values
- Stocks with no historical snapshots

**Browser testing**:
- Chrome (latest)
- Firefox (latest)
- Safari (if on macOS)

**Accessibility check**:
- Use browser dev tools accessibility checker
- Verify contrast ratios meet WCAG AA standards
- Test keyboard navigation (Tab key)

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### Color Coding Implementation

**Tailwind CSS classes**:
- `text-green-600` - Green for positive changes
- `text-red-600` - Red for negative changes
- `text-gray-500` - Gray for neutral/null

**Font weight**:
- `font-semibold` - Makes deltas stand out from regular text

**Conditional class application**:
```django
{% if item.quarter_delta > 0 %}text-green-600
{% elif item.quarter_delta < 0 %}text-red-600
{% else %}text-gray-500{% endif %}
```

**Why this approach?**:
- Simple conditional logic
- Native Django template syntax
- No JavaScript required
- Server-side rendering (fast)

### Table Layout Design

**Column groups**:
1. Stock info (1 column)
2. Current value (1 column)
3. Previous quarter (3 columns: value, delta $, delta %)
4. Year ago (3 columns: value, delta $, delta %)

**Visual separation**:
- Border between column groups (`border-l-2`)
- Colored borders (blue for quarter, purple for year)
- Colspan headers for group labels

**Why this layout?**:
- Easy to scan horizontally
- Group related data together
- Clear comparison structure
- Follows convention (left to right = past to present)

### Delta Formatting

**Dollar format**:
- Positive: `+$10.00`
- Negative: `-$5.00`
- Zero: `$0.00`
- NULL: `-`

**Percentage format**:
- Positive: `+7.14%`
- Negative: `-3.33%`
- Zero: `0.00%`
- NULL: `-`

**Implementation**:
```django
{% if item.quarter_delta is not None %}
    {% if item.quarter_delta > 0 %}+{% endif %}${{ item.quarter_delta }}
{% else %}-{% endif %}
```

### Legend Explanation

**Purpose**: Help users understand color coding at a glance

**Design**:
- Centered below table
- Small color squares + labels
- Three states: Increased, Decreased, No Change/No Data

**Why include?**:
- Not all users understand color conventions
- Accessibility best practice
- Reinforces visual language

### Responsive Strategy

**Wide tables on mobile**:
- Problem: 8 columns don't fit on small screens
- Solution: Horizontal scroll wrapper
- Effect: User can swipe to see all columns

**Header adjustment**:
- Desktop: Buttons side by side
- Mobile: Buttons stack vertically
- Uses Tailwind responsive classes: `md:flex-row`

**Date badges**:
- Desktop: Side by side
- Mobile: May wrap to two lines (acceptable)

### Comparison Date Badges

**Purpose**: Show what periods are being compared

**Design**:
- Pill-shaped badges
- Blue for previous quarter
- Purple for year ago
- Clear date labels

**Example**:
- Previous Quarter: Oct 1, 2024
- Year Ago: Jan 1, 2024

### Empty State

**When shown**: No active curated stocks exist

**Design**:
- Yellow info box (not error red)
- Icon + message
- Explains how to add stocks

**Why needed**:
- New installations have no data
- User might deactivate all stocks
- Better than blank page

### Performance Considerations

**Template rendering**:
- Single page load
- No AJAX/JavaScript
- Fast server-side rendering

**Large datasets**:
- 50 stocks = 50 table rows (acceptable)
- 100+ stocks may need pagination (future)
- Client-side sorting could improve UX (future)

**Optimization ideas** (if needed):
- Add pagination (show 25/50 stocks per page)
- Add client-side table sorting
- Add search/filter box
- Cache rendered HTML

## Dependencies

- Task 039 completed (Backend view exists)
- Tailwind CSS in base.html
- Django template system
- SVG icons (inline)

## Reference

**Tailwind CSS colors**:
- https://tailwindcss.com/docs/text-color
- Green-600: `#059669`
- Red-600: `#dc2626`
- Gray-500: `#6b7280`

**Django template filters**:
- floatformat: https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#floatformat
- truncatewords: https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#truncatewords

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 5: Frontend Implementation
- Section 8: Implementation Tasks (Task 040)
