# Task 038: Per-Stock History Frontend Template

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create stock_history.html template
- [ ] Step 2: Add historical snapshots table
- [ ] Step 3: Add current valuation summary card
- [ ] Step 4: Add export CSV button
- [ ] Step 5: Add navigation links
- [ ] Step 6: Test responsive design
- [ ] Step 7: Manual UI testing

## Overview

Create a frontend template to display the complete valuation history for a single stock. The page will show quarterly snapshots in a responsive table format using Tailwind CSS, with current valuation summary, export functionality, and navigation back to the valuations list.

**Current State**:
- Backend view exists (Task 037)
- No template to render history data
- Users cannot visualize historical trends

**Target State**:
- Template at `scanner/templates/scanner/stock_history.html`
- Responsive Tailwind CSS table showing all snapshots
- Current valuation summary at top for comparison
- CSV export button linking to export view (Task 041)
- Navigation breadcrumbs and back button
- Empty state message when no history exists
- Mobile-friendly design

## High-Level Specifications

### Template Structure

```
Header
  - Stock symbol and title
  - Export CSV button + Back button

Current Valuation Summary Card
  - EPS Intrinsic Value
  - FCF Intrinsic Value
  - Last Calculation Date

Chart Placeholder
  - Message: "Chart visualization coming in Phase 6.1"

Historical Snapshots Table
  - Columns: Quarter, EPS Value, EPS, FCF Value, FCF/Share, Growth %, Return %
  - Rows: One per snapshot, ordered newest first
  - Responsive: Horizontal scroll on mobile

Empty State (if no history)
  - Yellow info box
  - Message explaining no snapshots yet
```

### Styling

- **Framework**: Tailwind CSS (already in base.html)
- **Components**: Cards, tables, buttons, badges
- **Colors**: Blue for primary actions, gray for neutral, yellow for warnings
- **Responsive**: Mobile-first design with `md:` and `lg:` breakpoints

## Relevant Files

### Files to Create
- `scanner/templates/scanner/stock_history.html` - Main template file

### Files to Modify
- `scanner/templates/scanner/valuations.html` - Add "View History" links (optional, can do later)

### Files for Testing
- Manual testing via browser (no automated template tests)

## Acceptance Criteria

### Template Requirements
- [ ] Template extends `base.html`
- [ ] Title block set to "{symbol} - Valuation History"
- [ ] Content block contains all UI elements
- [ ] Conditional rendering based on `has_history` flag
- [ ] Uses Tailwind CSS utility classes
- [ ] No inline styles

### Header Requirements
- [ ] H1 displays stock symbol
- [ ] Subtitle displays "Quarterly Valuation History"
- [ ] Export CSV button with download icon
- [ ] Back to Valuations button
- [ ] Flexbox layout for header elements

### Current Valuation Summary
- [ ] Card shows 3 columns: EPS value, FCF value, Last calculated
- [ ] Handles NULL values gracefully (shows "-")
- [ ] Responsive grid layout (1 column mobile, 3 columns desktop)

### Historical Table
- [ ] Table shows all 7 columns
- [ ] Data formatted correctly ($ for values, % for rates)
- [ ] NULL values show as "-"
- [ ] Quarter labels use `quarter_label` property
- [ ] Hover effect on rows
- [ ] Responsive with horizontal scroll wrapper

### Empty State
- [ ] Shows when `has_history` is False
- [ ] Yellow info box with icon
- [ ] Clear message explaining no data yet
- [ ] Suggests when data will appear

### Navigation
- [ ] Export CSV button links to correct URL (with symbol parameter)
- [ ] Back button links to `scanner:valuations`
- [ ] Both buttons styled consistently

### Responsive Design
- [ ] Desktop (≥768px): Full layout with 3-column grid
- [ ] Tablet (640-767px): Adjusted spacing, table scrolls
- [ ] Mobile (<640px): Single column, table scrolls horizontally
- [ ] No horizontal overflow on any device

## Implementation Steps

### Step 1: Create stock_history.html template

Create the base template structure.

**File to create**: `scanner/templates/scanner/stock_history.html`

**Content**:
```django
{% extends "base.html" %}
{% load static %}

{% block title %}{{ stock.symbol }} - Valuation History{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-6">
    <!-- Header -->
    <div class="mb-6">
        <div class="flex justify-between items-center">
            <div>
                <h1 class="text-3xl font-bold text-gray-900">{{ stock.symbol }}</h1>
                <p class="text-gray-600 mt-1">{{ stock.name }}</p>
                <p class="text-sm text-gray-500">Quarterly Valuation History</p>
            </div>
            <div class="flex gap-3">
                <a href="{% url 'scanner:export_stock_history' stock.symbol %}"
                   class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                    Export CSV
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

    {% if has_history %}
        <!-- Current Valuation Summary -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-semibold mb-4 text-gray-900">Current Valuation</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <p class="text-sm text-gray-600 mb-1">EPS Intrinsic Value</p>
                    <p class="text-2xl font-bold text-gray-900">
                        {% if stock.intrinsic_value %}${{ stock.intrinsic_value }}{% else %}-{% endif %}
                    </p>
                </div>
                <div>
                    <p class="text-sm text-gray-600 mb-1">FCF Intrinsic Value</p>
                    <p class="text-2xl font-bold text-gray-900">
                        {% if stock.intrinsic_value_fcf %}${{ stock.intrinsic_value_fcf }}{% else %}-{% endif %}
                    </p>
                </div>
                <div>
                    <p class="text-sm text-gray-600 mb-1">Last Calculated</p>
                    <p class="text-lg font-semibold text-gray-900">
                        {% if stock.last_calculation_date %}{{ stock.last_calculation_date|date:"M d, Y" }}{% else %}Never{% endif %}
                    </p>
                </div>
            </div>
        </div>

        <!-- Chart Placeholder -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-semibold mb-4 text-gray-900">Trend Chart</h2>
            <div class="h-64 flex items-center justify-center bg-gray-50 rounded border-2 border-dashed border-gray-300">
                <p class="text-gray-500 text-center">
                    <svg class="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                    </svg>
                    Chart visualization coming in Phase 6.1
                </p>
            </div>
        </div>

        <!-- Historical Snapshots Table -->
        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-xl font-semibold text-gray-900">Historical Snapshots</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quarter</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">EPS Value</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Current EPS</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">FCF Value</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">FCF/Share</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Growth %</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Return %</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {% for snapshot in history %}
                        <tr class="hover:bg-gray-50 transition">
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                {{ snapshot.quarter_label }}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {% if snapshot.intrinsic_value %}${{ snapshot.intrinsic_value }}{% else %}-{% endif %}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                {% if snapshot.current_eps %}${{ snapshot.current_eps }}{% else %}-{% endif %}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {% if snapshot.intrinsic_value_fcf %}${{ snapshot.intrinsic_value_fcf }}{% else %}-{% endif %}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                {% if snapshot.current_fcf_per_share %}${{ snapshot.current_fcf_per_share }}{% else %}-{% endif %}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                {{ snapshot.eps_growth_rate }}%
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                {{ snapshot.desired_return }}%
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    {% else %}
        <!-- No History Message -->
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <div class="flex items-start">
                <svg class="w-6 h-6 text-yellow-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-yellow-800">No Historical Data</h3>
                    <p class="mt-2 text-sm text-yellow-700">
                        No quarterly snapshots have been created for {{ stock.symbol }} yet.
                        Historical data will appear after the next quarterly snapshot is created
                        (Jan 1, Apr 1, Jul 1, Oct 1).
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
# Check for Django template syntax errors
uv run python manage.py check --deploy
```

### Step 2: Add historical snapshots table

The table is already included in Step 1. Verify it renders correctly.

**Test with sample data**:
```bash
# Django shell - create test snapshot
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal

>>> stock = CuratedStock.objects.filter(active=True).first()
>>> if stock:
...     ValuationHistory.objects.create(
...         stock=stock,
...         snapshot_date=date(2025, 1, 1),
...         intrinsic_value=Decimal("150.00"),
...         current_eps=Decimal("6.00"),
...         eps_growth_rate=Decimal("10.0"),
...         eps_multiple=Decimal("20.0"),
...         intrinsic_value_fcf=Decimal("145.00"),
...         current_fcf_per_share=Decimal("7.00"),
...         fcf_growth_rate=Decimal("10.0"),
...         fcf_multiple=Decimal("20.0"),
...         desired_return=Decimal("15.0"),
...         projection_years=5,
...     )
>>> exit()
```

**View in browser**:
```
http://localhost:8000/scanner/valuations/history/[SYMBOL]/
```

**Verify table displays**:
- All 7 columns visible
- Data formatted correctly
- Quarter label shows "Q1 2025"
- NULL values show "-"

### Step 3: Add current valuation summary card

Already included in Step 1. Verify it displays correctly.

**Check**:
- 3-column grid on desktop
- Single column on mobile
- Handles NULL intrinsic values
- Date formatted properly

### Step 4: Add export CSV button

Already included in Step 1. The button links to export view (Task 041).

**Verify button**:
- Links to `scanner:export_stock_history` with symbol parameter
- Has download icon
- Blue background with hover effect
- Positioned in header

**Note**: Button will 404 until Task 041 (CSV export) is completed.

### Step 5: Add navigation links

Already included in Step 1.

**Verify links**:
- Back button links to `scanner:valuations`
- Both buttons responsive on mobile
- Icons display correctly

### Step 6: Test responsive design

Test layout on different screen sizes.

**Desktop testing** (≥768px):
```
Browser DevTools → Responsive Design Mode → 1200px width
```

**Verify**:
- Current valuation summary: 3 columns
- Table: Full width, no scroll
- Buttons: Side by side in header

**Tablet testing** (640-767px):
```
Browser DevTools → 768px width
```

**Verify**:
- Current valuation summary: 3 columns (might stack at 640px)
- Table: Horizontal scroll if needed
- Buttons: May stack vertically

**Mobile testing** (<640px):
```
Browser DevTools → iPhone SE (375px width)
```

**Verify**:
- Current valuation summary: Single column stacked
- Table: Horizontal scroll enabled
- Buttons: Stacked vertically
- Text readable without zooming

### Step 7: Manual UI testing

Comprehensive manual testing of all features.

**Test Checklist**:
```
[ ] Page loads without errors
[ ] Stock symbol and name display correctly
[ ] Current valuation summary shows correct data
[ ] Historical table shows all snapshots
[ ] Quarter labels formatted correctly (Q1 2025, Q2 2024, etc.)
[ ] NULL values show as "-" (not "None")
[ ] Dollar amounts formatted with $ prefix
[ ] Percentages show % suffix
[ ] Table rows have hover effect
[ ] Export CSV button present (may 404 until Task 041)
[ ] Back to Valuations button works
[ ] Empty state displays when no history exists
[ ] Empty state message is clear and helpful
[ ] No JavaScript console errors
[ ] No layout overflow on any device size
[ ] Colors consistent with site theme
[ ] Typography readable and consistent
```

**Test with multiple stocks**:
- Stock with many snapshots (5+)
- Stock with one snapshot
- Stock with no snapshots
- Stock with NULL intrinsic values

**Browser testing**:
- Chrome (latest)
- Firefox (latest)
- Safari (if on macOS)

**Cleanup test data**:
```bash
uv run python manage.py shell

>>> from scanner.models import ValuationHistory
>>> # Delete test snapshots if needed
>>> ValuationHistory.objects.filter(notes__contains="test").delete()
>>> exit()
```

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### Tailwind CSS Classes Used

**Layout**:
- `container mx-auto px-4 py-6` - Container with responsive padding
- `flex justify-between items-center` - Header layout
- `grid grid-cols-1 md:grid-cols-3 gap-4` - Responsive grid

**Components**:
- `bg-white rounded-lg shadow-md` - Card styling
- `px-6 py-4` - Padding utilities
- `text-gray-900`, `text-gray-600`, `text-gray-500` - Text colors
- `hover:bg-gray-50` - Hover states

**Typography**:
- `text-3xl font-bold` - Page title
- `text-xl font-semibold` - Section headings
- `text-sm text-gray-600` - Labels

**Buttons**:
- `inline-flex items-center px-4 py-2` - Button base
- `bg-blue-600 text-white rounded-lg hover:bg-blue-700` - Primary button
- `bg-gray-200 text-gray-700 hover:bg-gray-300` - Secondary button

### Chart Placeholder

**Why a placeholder?**:
- Chart.js integration is Phase 6.1 (future enhancement)
- Better to show placeholder than empty space
- Sets user expectation for future feature
- Maintains consistent page layout

**Future implementation**:
- Replace placeholder div with `<canvas>` element
- Add Chart.js script to base.html
- Pass historical data as JSON to JavaScript
- Render line chart with EPS and FCF trends

### Empty State Design

**Best practices**:
- Icon + text combination
- Yellow background (informational, not error)
- Explains why no data exists
- Tells user when data will appear
- Non-alarming language

**Example message**:
> "No quarterly snapshots have been created for AAPL yet. Historical data will appear after the next quarterly snapshot is created (Jan 1, Apr 1, Jul 1, Oct 1)."

### Table Design Decisions

**Why these columns?**:
- Quarter: Easy to scan chronologically
- EPS Value: Primary valuation result
- Current EPS: Shows underlying data
- FCF Value: Alternative valuation
- FCF/Share: Shows underlying data
- Growth %: Shows DCF assumption
- Return %: Shows DCF assumption

**What's not shown** (to keep table simple):
- EPS multiple, FCF multiple (consistent across time)
- Projection years (always 5)
- Preferred method (shown in comparison report)
- Notes field (rarely used)

**How to access full details**:
- Django admin interface
- CSV export (all fields)

### Responsive Table Strategy

**Problem**: Wide tables don't fit on mobile

**Solution**: Horizontal scroll wrapper
```html
<div class="overflow-x-auto">
    <table class="min-w-full">
        ...
    </table>
</div>
```

**Effect**:
- Table maintains full width
- User can swipe horizontally on mobile
- Better than hiding columns or stacking rows

### Accessibility Considerations

**Implemented**:
- Semantic HTML (table, th, td)
- Proper heading hierarchy (h1, h2)
- Alt text on icons (via SVG)
- Color contrast meets WCAG AA standards

**Future enhancements**:
- ARIA labels for icon-only buttons
- Screen reader announcements for data updates
- Keyboard navigation for table

## Dependencies

- Task 037 completed (Backend view exists)
- Tailwind CSS configured in base.html
- Django template system
- SVG icons (inline, no external dependencies)

## Reference

**Tailwind CSS documentation**:
- https://tailwindcss.com/docs
- Table styling: https://tailwindcss.com/docs/divide-width
- Responsive design: https://tailwindcss.com/docs/responsive-design

**Django templates**:
- https://docs.djangoproject.com/en/5.1/topics/templates/
- Built-in filters: https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#built-in-filter-reference

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 5: Frontend Implementation
- Section 8: Implementation Tasks (Task 038)
