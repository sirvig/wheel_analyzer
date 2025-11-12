# Phase 6.1: Visualizations and Advanced Analytics

## Overview

Phase 6.1 enhances the Phase 6 historical valuation system with interactive Chart.js visualizations and intermediate-level analytics. This phase focuses on helping users understand valuation trends, compare DCF methods, and analyze the sensitivity of intrinsic value calculations.

**Scope**: Core visualizations and analytics only. REST API, historical price tracking, and notification systems are deferred to future phases.

**Dependencies**: Requires Phase 6 completion (ValuationHistory model and quarterly snapshots)

**Estimated Effort**: 8-12 hours across 6 tasks

**Target**: 277-287 tests (247 existing + 30-40 new Phase 6.1 tests)

---

## Objectives

1. **Visualize Trends**: Create interactive line charts showing intrinsic value changes over time
2. **Compare Methods**: Enable visual comparison between EPS-based and FCF-based DCF valuations
3. **Analyze Volatility**: Calculate and display valuation volatility metrics (standard deviation, coefficient of variation)
4. **Calculate CAGR**: Compute compound annual growth rate for intrinsic value changes
5. **Correlation Analysis**: Show correlation between EPS and FCF methods across stocks
6. **Sensitivity Analysis**: Demonstrate how changes in DCF assumptions affect intrinsic value
7. **User-Friendly UX**: Provide both dedicated analytics page and contextual embedded charts

---

## Technical Stack

### Frontend
- **Chart.js 4.x** - JavaScript charting library (CDN or npm install)
- **Tailwind CSS** - Existing styling framework for chart containers
- **HTMX** - Existing dynamic updates (optional for chart refreshes)
- **Vanilla JavaScript** - Chart initialization and data handling

### Backend
- **Django Views** - Serve chart data and analytics
- **Python Analytics Module** - `scanner/analytics.py` for calculations
- **NumPy** (optional) - Statistical calculations (if not using stdlib)
- **QuerySets** - Leverage Django ORM for efficient data retrieval

### Database
- **PostgreSQL** - Existing database (no schema changes needed)
- **ValuationHistory model** - Source of historical data
- **CuratedStock model** - Current valuations and metadata

---

## Key Features

### 1. Dedicated Analytics Page (`/scanner/valuations/analytics/`)

**Purpose**: Comprehensive analytics dashboard with all visualizations and metrics

**Components**:
- **Portfolio Overview Section**:
  - Total stocks with valuation history
  - Average intrinsic value across portfolio
  - Portfolio-wide volatility metrics
  - Date range selector for analysis period

- **Trend Charts Section**:
  - Line chart: All stocks' intrinsic values over time (multi-line)
  - Toggle between EPS method, FCF method, or preferred method
  - Interactive tooltips showing values on hover
  - Legend with stock symbols (clickable to show/hide lines)

- **Method Comparison Section**:
  - Scatter plot: EPS vs. FCF intrinsic values for all stocks
  - Bar chart: Average difference between methods by stock
  - Correlation coefficient displayed prominently

- **Analytics Table Section**:
  - Stock-by-stock analytics table with sortable columns:
    - Symbol
    - Latest intrinsic value (preferred method)
    - Volatility (std dev)
    - CAGR (if ≥2 quarters of data)
    - Method correlation
    - Data points count
  - CSV export button for analytics data

- **Sensitivity Analysis Section** (per-stock basis):
  - Stock selector dropdown
  - Interactive sliders/inputs for DCF assumptions:
    - Growth rate (+/- 5%)
    - Discount rate (+/- 3%)
    - Terminal growth rate (+/- 2%)
  - Real-time intrinsic value recalculation
  - Tornado chart showing assumption sensitivity

**Navigation**:
- Link from main valuations page header
- Breadcrumb navigation
- "View Details" buttons linking to per-stock history

---

### 2. Embedded Charts on Stock History Page

**Location**: `/scanner/valuations/history/<symbol>/`

**Additions**:
- **Line Chart**: Intrinsic value trend for the specific stock
  - Dual lines: EPS method (blue) and FCF method (green)
  - Highlight preferred method with thicker line
  - Show quarterly snapshots as data points
  - Responsive sizing (full width of content area)

- **Analytics Card** (below chart):
  - Volatility: Standard deviation and coefficient of variation
  - CAGR: Compound annual growth rate (if ≥2 quarters)
  - Latest change: % change from previous quarter
  - Method divergence: % difference between EPS and FCF methods

- **Quick Stats Boxes** (above chart):
  - Highest IV recorded (with date)
  - Lowest IV recorded (with date)
  - Average IV across all snapshots
  - Current IV vs. average (% above/below)

**Placement**: Insert between current valuation summary card and historical snapshots table

---

### 3. Embedded Chart on Comparison Report Page

**Location**: `/scanner/valuations/comparison/`

**Addition**:
- **Bar Chart**: Compare current intrinsic values across all stocks
  - Grouped bars: EPS method, FCF method, Preferred method
  - Color-coded by method
  - X-axis: Stock symbols
  - Y-axis: Intrinsic value ($)
  - Responsive design (horizontal scroll for many stocks)

**Placement**: Insert below page header, above comparison table

---

### 4. Analytics Module (`scanner/analytics.py`)

**Purpose**: Centralized calculations for all analytics

**Functions**:

```python
def calculate_volatility(values: List[float]) -> Dict[str, float]:
    """Calculate standard deviation and coefficient of variation."""
    # Returns: {'std_dev': float, 'coefficient_of_variation': float}

def calculate_cagr(start_value: float, end_value: float, periods: int) -> float:
    """Calculate compound annual growth rate."""
    # periods = number of quarters (divide by 4 for annual rate)

def calculate_correlation(x_values: List[float], y_values: List[float]) -> float:
    """Calculate Pearson correlation coefficient between two series."""

def calculate_sensitivity(
    stock: CuratedStock,
    assumption: str,
    delta: float
) -> Dict[str, float]:
    """Recalculate IV with adjusted assumption, return % change."""
    # assumption: 'growth_rate', 'discount_rate', 'terminal_growth_rate'
    # delta: percentage point change (e.g., 0.02 for +2%)

def get_stock_analytics(symbol: str) -> Dict[str, Any]:
    """Get comprehensive analytics for a single stock."""
    # Returns dict with volatility, CAGR, correlation, data points, etc.

def get_portfolio_analytics() -> Dict[str, Any]:
    """Get portfolio-wide analytics across all stocks."""
    # Returns aggregate metrics and per-stock summaries
```

**Design Principles**:
- Pure functions (no side effects)
- Type hints for all functions
- Comprehensive docstrings
- Handle edge cases (< 2 data points, None values, etc.)
- Return structured dictionaries (not tuples)

---

### 5. Context Processors (Optional)

**File**: `scanner/context_processors.py`

**Purpose**: Make analytics easily available in templates

```python
def analytics_enabled(request):
    """Check if user has access to analytics features."""
    return {
        'analytics_enabled': request.user.is_authenticated,
        'chart_js_version': '4.4.1',
    }
```

**Configuration**: Add to `settings.py` TEMPLATES context_processors

---

## Architecture Decisions

### 1. Client-Side vs. Server-Side Rendering

**Decision**: Client-side chart rendering with Chart.js

**Rationale**:
- Interactive charts (zoom, pan, tooltips)
- No additional server load for re-rendering
- Better user experience with animations
- Chart.js is lightweight (~200KB) and well-documented

**Trade-offs**:
- Requires JavaScript enabled (acceptable for modern web app)
- Initial data must be serialized to JSON in template

---

### 2. Data Fetching Strategy

**Decision**: Embed chart data in template context (no AJAX for initial load)

**Rationale**:
- Simpler implementation (no additional API endpoints needed)
- Faster initial page load (one request instead of two)
- Sufficient for current data volumes (<50 stocks, <40 quarters each)

**Future Enhancement**: If performance becomes an issue, migrate to AJAX endpoints

---

### 3. Analytics Calculation Timing

**Decision**: Calculate analytics on-demand (view layer)

**Rationale**:
- Data changes infrequently (quarterly snapshots)
- Calculations are fast (<100ms for portfolio analytics)
- No need for pre-computation or caching yet

**Future Enhancement**: Add Redis caching if analytics page becomes slow (>500ms)

---

### 4. Chart Library Choice

**Decision**: Chart.js over Plotly, D3.js, or Highcharts

**Rationale**:
- **Chart.js**: Simple API, good documentation, MIT license, adequate for our needs
- **Plotly**: Overkill for our use case, larger bundle size
- **D3.js**: Too low-level, requires more code for basic charts
- **Highcharts**: Excellent but commercial license required for business use

---

### 5. Sensitivity Analysis Approach

**Decision**: Frontend sliders + backend recalculation on submit

**Rationale**:
- Avoids exposing DCF calculation logic to frontend
- Maintains single source of truth (valuation.py)
- Security: User can't manipulate calculations directly

**Implementation**: HTMX form submission to update sensitivity results partial

---

## Implementation Tasks

### Task 1: Create Analytics Module

**File**: `scanner/analytics.py`

**Subtasks**:
1. Create new Python module file
2. Implement `calculate_volatility()` function
   - Use statistics.stdev() from stdlib
   - Handle edge cases (empty list, single value, None values)
   - Calculate coefficient of variation (stdev / mean)
3. Implement `calculate_cagr()` function
   - Formula: `((end_value / start_value) ^ (1 / years)) - 1`
   - Convert quarters to years (periods / 4)
   - Handle zero/negative start values
4. Implement `calculate_correlation()` function
   - Use statistics.correlation() (Python 3.10+) or numpy.corrcoef()
   - Handle mismatched lengths and missing values
5. Implement `calculate_sensitivity()` function
   - Import DCF functions from valuation.py
   - Adjust one assumption at a time
   - Return dict: `{'original_iv': float, 'adjusted_iv': float, 'change_pct': float}`
6. Implement `get_stock_analytics()` function
   - Query ValuationHistory for stock snapshots
   - Extract EPS and FCF IV values
   - Calculate all metrics (volatility, CAGR, correlation)
   - Return comprehensive dict
7. Implement `get_portfolio_analytics()` function
   - Iterate through all CuratedStock objects with history
   - Aggregate per-stock analytics
   - Calculate portfolio-wide averages
8. Add comprehensive docstrings and type hints
9. Write unit tests for each function

**Acceptance Criteria**:
- All functions have 100% test coverage
- Functions handle edge cases gracefully
- Type hints and docstrings are complete
- No external dependencies beyond Python stdlib (or numpy if needed)

**Estimated Time**: 2-3 hours

---

### Task 2: Create Dedicated Analytics Page

**Files**:
- `scanner/views.py` - Add `analytics_view()` function
- `scanner/urls.py` - Add URL route
- `templates/scanner/analytics.html` - New template

**Subtasks**:

1. **View Function** (`scanner/views.py`):
   ```python
   @login_required
   def analytics_view(request):
       """Display comprehensive analytics dashboard."""
       portfolio_analytics = get_portfolio_analytics()

       # Prepare chart data
       chart_data = {
           'labels': [],  # Quarterly dates
           'datasets': []  # Per-stock IV series
       }

       for stock in CuratedStock.objects.filter(is_active=True):
           history = ValuationHistory.objects.filter(
               stock=stock
           ).order_by('snapshot_date')

           if history.exists():
               chart_data['datasets'].append({
                   'label': stock.symbol,
                   'data': [h.get_effective_intrinsic_value() for h in history],
                   'borderColor': generate_color(stock.symbol),
                   'fill': False
               })

       context = {
           'analytics': portfolio_analytics,
           'chart_data': json.dumps(chart_data),
           'date_range': 'All Time',  # Can be made dynamic
       }
       return render(request, 'scanner/analytics.html', context)
   ```

2. **URL Route** (`scanner/urls.py`):
   ```python
   path('valuations/analytics/', views.analytics_view, name='analytics'),
   ```

3. **Template** (`templates/scanner/analytics.html`):
   - Extend `base.html`
   - Include Chart.js from CDN (`<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>`)
   - Create portfolio overview section with cards
   - Add canvas element for trend chart: `<canvas id="trendChart"></canvas>`
   - Add JavaScript to initialize Chart.js:
     ```javascript
     const ctx = document.getElementById('trendChart').getContext('2d');
     const chartData = {{ chart_data|safe }};

     new Chart(ctx, {
         type: 'line',
         data: chartData,
         options: {
             responsive: true,
             plugins: {
                 title: {
                     display: true,
                     text: 'Intrinsic Value Trends'
                 },
                 legend: {
                     display: true,
                     position: 'bottom'
                 }
             },
             scales: {
                 y: {
                     beginAtZero: false,
                     title: {
                         display: true,
                         text: 'Intrinsic Value ($)'
                     }
                 }
             }
         }
     });
     ```
   - Create analytics table with sortable columns (use Tailwind classes)
   - Add method comparison section placeholder
   - Add sensitivity analysis section with stock selector and sliders

4. **Navigation Updates**:
   - Add "Analytics" button to `templates/scanner/valuations.html` header
   - Add breadcrumb navigation to analytics page

**Acceptance Criteria**:
- Analytics page renders without errors
- Trend chart displays correctly with all stocks
- Portfolio metrics are accurate and formatted
- Analytics table is sortable by column
- Page is responsive (mobile-friendly)
- Dark mode styling is consistent

**Estimated Time**: 3-4 hours

---

### Task 3: Add Embedded Chart to Stock History Page

**Files**:
- `scanner/views.py` - Update `stock_history_view()` function
- `templates/scanner/stock_history.html` - Update template

**Subtasks**:

1. **View Function Update** (`scanner/views.py`):
   ```python
   def stock_history_view(request, symbol):
       # Existing code...

       # Add analytics data
       stock_analytics = get_stock_analytics(symbol)

       # Prepare chart data
       history = ValuationHistory.objects.filter(
           stock=stock
       ).order_by('snapshot_date')

       chart_data = {
           'labels': [h.quarter_label for h in history],
           'datasets': [
               {
                   'label': 'EPS Method',
                   'data': [h.eps_intrinsic_value for h in history],
                   'borderColor': 'rgb(59, 130, 246)',  # Blue
                   'borderWidth': 2,
               },
               {
                   'label': 'FCF Method',
                   'data': [h.fcf_intrinsic_value for h in history],
                   'borderColor': 'rgb(34, 197, 94)',  # Green
                   'borderWidth': 2,
               }
           ]
       }

       context = {
           # Existing context...
           'analytics': stock_analytics,
           'chart_data': json.dumps(chart_data),
       }
       return render(request, 'scanner/stock_history.html', context)
   ```

2. **Template Update** (`templates/scanner/stock_history.html`):
   - Add Chart.js CDN (if not already in base.html)
   - Insert "Quick Stats" boxes section above chart
   - Insert canvas element for line chart
   - Initialize Chart.js with dual-line configuration
   - Add analytics card below chart
   - Update dark mode styles for chart containers

3. **Quick Stats Implementation**:
   - Calculate highest/lowest/average IV in view
   - Display in Tailwind card grid (4 columns on desktop)
   - Color-code current vs. average (green if above, red if below)

**Acceptance Criteria**:
- Chart displays EPS and FCF methods as separate lines
- Quick stats boxes show correct values
- Analytics card displays volatility, CAGR, and change metrics
- Chart is responsive and maintains aspect ratio
- Dark mode renders correctly
- Page load time remains <300ms

**Estimated Time**: 2 hours

---

### Task 4: Add Embedded Chart to Comparison Report Page

**Files**:
- `scanner/views.py` - Update `valuation_comparison_view()` function
- `templates/scanner/valuation_comparison.html` - Update template

**Subtasks**:

1. **View Function Update** (`scanner/views.py`):
   ```python
   def valuation_comparison_view(request):
       # Existing code...

       # Prepare bar chart data
       stocks = CuratedStock.objects.filter(is_active=True).order_by('symbol')

       chart_data = {
           'labels': [stock.symbol for stock in stocks],
           'datasets': [
               {
                   'label': 'EPS Method',
                   'data': [stock.eps_intrinsic_value or 0 for stock in stocks],
                   'backgroundColor': 'rgba(59, 130, 246, 0.8)',
               },
               {
                   'label': 'FCF Method',
                   'data': [stock.fcf_intrinsic_value or 0 for stock in stocks],
                   'backgroundColor': 'rgba(34, 197, 94, 0.8)',
               }
           ]
       }

       context = {
           # Existing context...
           'chart_data': json.dumps(chart_data),
       }
       return render(request, 'scanner/valuation_comparison.html', context)
   ```

2. **Template Update** (`templates/scanner/valuation_comparison.html`):
   - Insert canvas element below header, above table
   - Initialize Chart.js as grouped bar chart
   - Configure horizontal scrolling for many stocks
   - Add chart container with max-height and overflow

3. **Chart Configuration**:
   ```javascript
   new Chart(ctx, {
       type: 'bar',
       data: chartData,
       options: {
           responsive: true,
           maintainAspectRatio: false,
           plugins: {
               title: {
                   display: true,
                   text: 'Current Intrinsic Values by Method'
               }
           },
           scales: {
               y: {
                   beginAtZero: false,
                   title: {
                       display: true,
                       text: 'Intrinsic Value ($)'
                   }
               }
           }
       }
   });
   ```

**Acceptance Criteria**:
- Bar chart displays all stocks with grouped bars
- Chart is scrollable if too many stocks (>20)
- Colors match EPS/FCF method conventions
- Chart height is fixed (400px) with responsive width
- Dark mode styling is consistent

**Estimated Time**: 1.5 hours

---

### Task 5: Implement Sensitivity Analysis

**Files**:
- `scanner/views.py` - Add `sensitivity_analysis_view()` function
- `scanner/urls.py` - Add URL route
- `templates/scanner/partials/sensitivity_results.html` - New partial

**Subtasks**:

1. **View Function** (`scanner/views.py`):
   ```python
   @login_required
   def sensitivity_analysis_view(request):
       """Calculate sensitivity of IV to DCF assumptions."""
       if request.method == 'POST':
           symbol = request.POST.get('symbol')
           assumption = request.POST.get('assumption')
           delta = float(request.POST.get('delta', 0))

           stock = get_object_or_404(CuratedStock, symbol=symbol)
           sensitivity = calculate_sensitivity(stock, assumption, delta)

           context = {
               'stock': stock,
               'assumption': assumption,
               'delta': delta,
               'sensitivity': sensitivity,
           }
           return render(request, 'scanner/partials/sensitivity_results.html', context)

       # GET request: show form
       stocks = CuratedStock.objects.filter(is_active=True).order_by('symbol')
       return render(request, 'scanner/analytics.html', {'stocks': stocks})
   ```

2. **URL Route** (`scanner/urls.py`):
   ```python
   path('valuations/sensitivity/', views.sensitivity_analysis_view, name='sensitivity_analysis'),
   ```

3. **Form in Analytics Template**:
   - Add form to sensitivity analysis section
   - Stock selector dropdown
   - Assumption radio buttons (growth_rate, discount_rate, terminal_growth_rate)
   - Range slider for delta (-5% to +5%)
   - HTMX attributes: `hx-post="/scanner/valuations/sensitivity/" hx-target="#sensitivity-results"`

4. **Results Partial Template**:
   - Display original IV vs. adjusted IV
   - Show percentage change with color coding
   - Show tornado chart (if multiple assumptions tested)
   - Format values with currency and percentage filters

5. **Analytics Module Update**:
   - Ensure `calculate_sensitivity()` uses existing DCF functions from `valuation.py`
   - Import `calculate_dcf_eps()` and `calculate_dcf_fcf()`
   - Modify assumption parameter, recalculate, return diff

**Acceptance Criteria**:
- Sensitivity form submits via HTMX without page reload
- Results update in real-time (<1 second)
- Calculations are accurate (verified against manual DCF)
- User can test multiple assumptions sequentially
- Error handling for invalid inputs

**Estimated Time**: 2-3 hours

---

### Task 6: Testing and Documentation

**Subtasks**:

1. **Unit Tests** (`scanner/tests/test_analytics.py`):
   - Test `calculate_volatility()` with various data sets
   - Test `calculate_cagr()` with edge cases (zero, negative)
   - Test `calculate_correlation()` with perfect/no correlation
   - Test `calculate_sensitivity()` with each assumption type
   - Test `get_stock_analytics()` with mock ValuationHistory data
   - Test `get_portfolio_analytics()` with multiple stocks

2. **View Tests** (`scanner/tests/test_analytics_views.py`):
   - Test analytics page renders for authenticated user
   - Test analytics page redirects for anonymous user
   - Test chart data is correctly serialized to JSON
   - Test sensitivity analysis form submission
   - Test embedded charts on stock history page
   - Test embedded chart on comparison page

3. **Integration Tests**:
   - Test full analytics workflow (create snapshots → view analytics)
   - Test chart rendering with real data (use factories)
   - Test analytics calculations match expected values

4. **Template Tests**:
   - Verify Chart.js initializes without JavaScript errors
   - Test responsive behavior (mobile, tablet, desktop)
   - Test dark mode styling on all new templates

5. **Documentation Updates**:
   - Update `CLAUDE.md` with analytics module documentation
   - Update `README.md` with analytics feature description
   - Update `reference/ROADMAP.md` with Phase 6.1 completion status
   - Add inline code comments for Chart.js configurations

6. **Manual Testing Checklist**:
   - [ ] Analytics page loads and displays portfolio metrics
   - [ ] Trend chart shows all stocks correctly
   - [ ] Stock history page shows embedded chart
   - [ ] Comparison page shows bar chart
   - [ ] Sensitivity analysis updates on form submit
   - [ ] All charts are responsive
   - [ ] Dark mode works on all pages
   - [ ] CSV export still works on analytics table
   - [ ] Navigation links work correctly
   - [ ] Page load times are acceptable (<500ms)

**Acceptance Criteria**:
- All tests pass (target: 277-287 total tests)
- Test coverage for analytics.py is 100%
- View test coverage for new views is >90%
- No console errors in browser dev tools
- Documentation is updated and accurate

**Estimated Time**: 2-3 hours

---

## Testing Strategy

### Test Types

1. **Unit Tests** (`test_analytics.py`):
   - Pure function tests for analytics module
   - Mock ValuationHistory data
   - Test edge cases and error handling

2. **View Tests** (`test_analytics_views.py`):
   - Test view responses (200, 302 redirects)
   - Test context data correctness
   - Test authentication requirements
   - Test HTMX partial rendering

3. **Integration Tests** (`test_analytics_integration.py`):
   - End-to-end workflows
   - Real database queries (use pytest-django fixtures)
   - Test chart data generation pipeline

4. **Frontend Tests** (Manual):
   - Chart.js rendering
   - Responsive design
   - Dark mode
   - Interactive features (tooltips, legend clicks)

### Test Data

Use existing factories from `scanner/factories.py`:
- `CuratedStockFactory` - Create test stocks
- Create new `ValuationHistoryFactory` - Generate quarterly snapshots

Example factory:
```python
class ValuationHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ValuationHistory

    stock = factory.SubFactory(CuratedStockFactory)
    snapshot_date = factory.Faker('date_between', start_date='-2y', end_date='today')
    eps_intrinsic_value = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    fcf_intrinsic_value = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    # ... other fields
```

### Coverage Goals

- **Analytics module**: 100% line coverage
- **Views**: >90% line coverage (exclude error paths that are hard to trigger)
- **Templates**: Manual verification (no automated template testing)
- **Overall project**: Maintain >85% coverage

### Continuous Testing

- Run `just test` after each subtask
- Fix broken tests immediately before proceeding
- Use TDD approach for analytics functions (write tests first)

---

## Success Criteria

### Functional Requirements

- ✅ Analytics page displays portfolio-wide metrics and trends
- ✅ Stock history page shows embedded line chart with EPS/FCF methods
- ✅ Comparison page shows embedded bar chart
- ✅ Sensitivity analysis allows testing assumption changes
- ✅ All charts are interactive (tooltips, legends, zoom)
- ✅ Analytics calculations are accurate and verified
- ✅ All pages are mobile-responsive
- ✅ Dark mode is consistently styled

### Performance Requirements

- ✅ Analytics page loads in <500ms (with 26 stocks, 10 quarters each)
- ✅ Chart rendering completes in <200ms
- ✅ Sensitivity analysis responds in <1 second
- ✅ No N+1 query problems (use `select_related`, `prefetch_related`)

### Testing Requirements

- ✅ All tests pass (277-287 total, 100% pass rate)
- ✅ New analytics module has 100% test coverage
- ✅ No regression in existing tests (247 tests still pass)
- ✅ Manual testing checklist completed

### Code Quality Requirements

- ✅ All code passes `ruff` linting
- ✅ Type hints on all new functions
- ✅ Comprehensive docstrings
- ✅ No JavaScript console errors
- ✅ Follows Django best practices

### Documentation Requirements

- ✅ `ROADMAP.md` updated with Phase 6.1 completion
- ✅ `CLAUDE.md` includes analytics module documentation
- ✅ `README.md` mentions analytics features
- ✅ Inline code comments for complex logic

---

## Potential Challenges and Solutions

### Challenge 1: Chart.js Configuration Complexity

**Problem**: Chart.js has many configuration options; getting the right settings for responsive, dark-mode charts can be time-consuming.

**Solution**:
- Start with minimal configuration, iterate based on results
- Use Chart.js documentation examples as templates
- Test dark mode early (add CSS variables for colors)
- Consider creating a JavaScript utility function for common chart defaults

---

### Challenge 2: Performance with Many Stocks/Quarters

**Problem**: If portfolio grows to 100+ stocks with 40+ quarters each, chart rendering may slow down.

**Solution** (for now):
- Current scope (26 stocks, ~10 quarters) should perform fine
- Monitor analytics page load time
- If >500ms, consider:
  - Pagination or date range filters
  - Lazy loading charts (load on scroll)
  - Server-side aggregation

**Future Enhancement**: Add Redis caching for chart data if needed

---

### Challenge 3: Correlation Calculation with Missing Data

**Problem**: Some stocks may have sparse ValuationHistory (missing quarters), making correlation calculations unreliable.

**Solution**:
- Filter stocks with <4 data points from correlation analysis
- Show "Insufficient data" message in analytics table
- Consider interpolation for missing quarters (future enhancement)

---

### Challenge 4: Sensitivity Analysis Complexity

**Problem**: Exposing full DCF calculation to frontend for real-time sensitivity is complex.

**Solution**:
- Keep it server-side (HTMX form submission)
- Accept slower response time (~1 second) for accuracy
- Future: Consider WebSockets or Server-Sent Events for real-time updates

---

### Challenge 5: Dark Mode Chart Styling

**Problem**: Chart.js doesn't automatically detect dark mode; colors need manual adjustment.

**Solution**:
- Define CSS variables for chart colors in `styles.css`:
  ```css
  :root {
      --chart-text-color: #1f2937;
      --chart-grid-color: #e5e7eb;
  }

  .dark {
      --chart-text-color: #f9fafb;
      --chart-grid-color: #374151;
  }
  ```
- Pass these variables to Chart.js options via JavaScript:
  ```javascript
  const textColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--chart-text-color');
  ```

---

## Database Queries and Optimization

### Efficient Data Fetching

**Problem**: Loading ValuationHistory for all stocks can trigger N+1 queries.

**Solution**: Use `prefetch_related` and `select_related`:

```python
stocks = CuratedStock.objects.filter(is_active=True).prefetch_related(
    Prefetch(
        'valuationhistory_set',
        queryset=ValuationHistory.objects.order_by('snapshot_date')
    )
)
```

### Query Count Target

- Analytics page: ≤10 queries (1 for stocks, 1 for history, rest for auth/session)
- Stock history page: ≤5 queries
- Comparison page: ≤8 queries

**Monitor**: Use Django Debug Toolbar in development to verify query counts

---

## Future Enhancements (Deferred)

### Phase 6.2: REST API (Deferred)

**Scope**:
- Django REST Framework integration
- API endpoints for chart data: `/api/v1/valuations/trends/`, `/api/v1/analytics/<symbol>/`
- Token authentication
- Rate limiting
- OpenAPI documentation

**Why Defer**: Focus on user-facing features first; API can be added later if external integrations are needed

---

### Phase 6.3: Notification System (Deferred)

**Scope**:
- Email alerts when IV changes by >20%
- Weekly digest emails with portfolio summary
- Celery + Redis for async task processing
- Django signals for event-driven notifications

**Why Defer**: Requires additional infrastructure (Celery workers); not critical for MVP

---

### Phase 8 Integration: Historical Price Tracking

**Future Integration**:
- Once Phase 8 adds stock prices, enhance charts:
  - Overlay price line on IV trend charts
  - Calculate price vs. IV divergence
  - Show undervaluation periods (price < IV)
  - Add "Buy zones" highlighting

**Preparation**: Design analytics module to easily integrate price data later

---

## File Structure Summary

### New Files

```
scanner/
├── analytics.py                                    # NEW: Analytics calculations module
├── tests/
│   ├── test_analytics.py                          # NEW: Unit tests for analytics
│   └── test_analytics_views.py                    # NEW: View tests for analytics

templates/scanner/
├── analytics.html                                  # NEW: Dedicated analytics dashboard
└── partials/
    └── sensitivity_results.html                    # NEW: Sensitivity analysis results
```

### Modified Files

```
scanner/
├── views.py                                        # MODIFIED: Add 3 new views + update 2 existing
├── urls.py                                         # MODIFIED: Add 2 new URL routes

templates/scanner/
├── stock_history.html                              # MODIFIED: Add embedded chart
├── valuation_comparison.html                       # MODIFIED: Add embedded chart
└── valuations.html                                 # MODIFIED: Add "Analytics" button

wheel_analyzer/
├── settings.py                                     # MODIFIED: Add context processor (optional)

reference/
├── ROADMAP.md                                      # MODIFIED: Update Phase 6.1 status
└── CLAUDE.md                                       # MODIFIED: Document analytics module

static/
└── css/
    └── styles.css                                  # MODIFIED: Add chart container styles
```

---

## Deployment Checklist

Before marking Phase 6.1 as complete:

- [ ] All 277-287 tests passing (100% pass rate)
- [ ] `ruff` linting passes with no errors
- [ ] Manual testing checklist completed
- [ ] Documentation updated (ROADMAP, CLAUDE, README)
- [ ] Git commit with descriptive message
- [ ] Backup database before deploying (just in case)
- [ ] Deploy to production environment
- [ ] Verify analytics page loads in production
- [ ] Verify charts render correctly in production
- [ ] Monitor production logs for errors (first 24 hours)

---

## Estimated Timeline

| Task | Description | Time Estimate |
|------|-------------|---------------|
| 1    | Create analytics module | 2-3 hours |
| 2    | Dedicated analytics page | 3-4 hours |
| 3    | Embedded chart (stock history) | 2 hours |
| 4    | Embedded chart (comparison) | 1.5 hours |
| 5    | Sensitivity analysis | 2-3 hours |
| 6    | Testing and documentation | 2-3 hours |
| **Total** | | **12.5-16.5 hours** |

**Recommended Sprint**: 2-3 days of focused development

---

## Notes for Implementation

1. **Start with Task 1** (analytics module) - all other tasks depend on it
2. **Test incrementally** - run tests after each function is complete
3. **Visual iteration** - expect to adjust chart styling multiple times
4. **User feedback** - after Task 2, get feedback on analytics page design before proceeding
5. **Performance monitoring** - use Django Debug Toolbar throughout development

---

## Conclusion

Phase 6.1 delivers high-value visualizations and analytics without over-complicating the system. By focusing on core features (trend charts, volatility, CAGR, sensitivity) and deferring REST API and notifications, we maintain a tight scope that can be completed in 2-3 days. The architecture supports future enhancements (Phase 8 price integration, Phase 6.2 API) without requiring major refactoring.

**Key Wins**:
- Interactive Chart.js visualizations on 3 pages
- Comprehensive analytics module with reusable functions
- Sensitivity analysis for DCF assumption testing
- Production-ready with 100% test pass rate
- Excellent foundation for future phases

**Next Steps After Completion**:
- Consider Phase 6.2 (REST API) if external integrations are needed
- Or proceed to Phase 7 (Individual Stock Scanning) for user-requested features
- Or jump to Phase 8 (Stock Price Integration) to unlock price vs. IV comparisons
