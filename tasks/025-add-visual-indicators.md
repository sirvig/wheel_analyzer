# Task 025: Update Options Results Template with Visual Indicators

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add badge to individual option rows
- [ ] Step 2: Add badge to accordion headers (stock-level status)
- [ ] Step 3: Add custom CSS for badge alignment (if needed)
- [ ] Step 4: Test visual indicators with various stock states

## Overview

Add Bootstrap badges to the options results template showing visual indicators for intrinsic value comparison. This provides users with immediate visual feedback on whether option strike prices are attractive relative to calculated intrinsic values.

The implementation adds:
- Bootstrap badges on each option row (green "✓ Good" / red "✗ High" / yellow "⚠ N/A")
- Bootstrap badge on accordion headers showing overall stock status
- Comparison logic using option strike price vs intrinsic value
- Graceful handling of NULL intrinsic values

## Current State Analysis

### Current Template Structure

The `templates/scanner/partials/options_results.html` currently displays:
- Accordion for each stock symbol
- Accordion header with stock ticker
- Accordion body with table of options
- Each option row shows: expiration, strike, price, delta, annual return

**Current accordion header**:
```html
<h2 class="accordion-header">
  <button class="accordion-button collapsed" ...>
    {{ symbol }} Options
  </button>
</h2>
```

**Current option row** (simplified):
```html
<tr>
  <td>{{ option.expiration }}</td>
  <td>{{ option.strike }}</td>
  <td>{{ option.price }}</td>
  <td>{{ option.delta }}</td>
  <td>{{ option.annual_return }}</td>
</tr>
```

### Current Context Available

From Task 024:
- `curated_stocks`: Dict of `{symbol: CuratedStock instance}`
- `options`: Dict of `{symbol: [option_dict, ...]}`

**Available in template**:
```django
{% for symbol, option_list in options.items %}
  {# Can access: curated_stocks.symbol.get_effective_intrinsic_value #}
  {% for option in option_list %}
    {# Can access: option.strike #}
  {% endfor %}
{% endfor %}
```

## Target State

### Visual Indicator Logic

**Individual option row badge**:
- Green "✓ Good": Strike ≤ Intrinsic Value
- Red "✗ High": Strike > Intrinsic Value  
- Yellow "⚠ N/A": Intrinsic Value is NULL

**Accordion header badge**:
- Green "✓": At least ONE option has strike ≤ IV
- Red "✗": ALL options have strike > IV
- Yellow "⚠": Intrinsic Value is NULL

### Badge Styling

Using Bootstrap 5 badges:
- Green: `<span class="badge bg-success">✓ Good</span>`
- Red: `<span class="badge bg-danger">✗ High</span>`
- Yellow: `<span class="badge bg-warning">⚠ N/A</span>`

### Example Output

**Accordion header with green badge**:
```html
<button class="accordion-button collapsed">
  <span class="badge bg-success me-2">✓</span> AAPL Options
</button>
```

**Option row with badges**:
```html
<tr>
  <td><span class="badge bg-success">✓ Good</span></td>
  <td>2025-12-19</td>
  <td>$145.00</td>
  <td>$2.50</td>
  <td>-0.15</td>
  <td>32.5%</td>
</tr>
```

## Implementation Steps

### Step 1: Add badge to individual option rows

Add a new column with badge indicator for each option.

**File to modify**: `templates/scanner/partials/options_results.html`

**Find the table header** (inside accordion body):
```html
<thead>
  <tr>
    <th>Expiration</th>
    <th>Strike</th>
    <th>Price</th>
    <th>Delta</th>
    <th>Annual Return</th>
  </tr>
</thead>
```

**Add new column at the beginning**:
```html
<thead>
  <tr>
    <th>Status</th>
    <th>Expiration</th>
    <th>Strike</th>
    <th>Price</th>
    <th>Delta</th>
    <th>Annual Return</th>
  </tr>
</thead>
```

**Find the option row** (inside tbody):
```html
{% for option in option_list %}
  <tr>
    <td>{{ option.expiration }}</td>
    <td>${{ option.strike }}</td>
    <td>${{ option.price }}</td>
    <td>{{ option.delta }}</td>
    <td>{{ option.annual_return }}%</td>
  </tr>
{% endfor %}
```

**Add badge logic at the beginning of the row**:
```django
{% for option in option_list %}
  <tr>
    <td>
      {% with stock=curated_stocks|dict_get:symbol %}
        {% if stock %}
          {% with iv=stock.get_effective_intrinsic_value %}
            {% if iv is None %}
              <span class="badge bg-warning">⚠ N/A</span>
            {% elif option.strike <= iv %}
              <span class="badge bg-success">✓ Good</span>
            {% else %}
              <span class="badge bg-danger">✗ High</span>
            {% endif %}
          {% endwith %}
        {% else %}
          <span class="badge bg-secondary">-</span>
        {% endif %}
      {% endwith %}
    </td>
    <td>{{ option.expiration }}</td>
    <td>${{ option.strike }}</td>
    <td>${{ option.price }}</td>
    <td>{{ option.delta }}</td>
    <td>{{ option.annual_return }}%</td>
  </tr>
{% endfor %}
```

**Note**: Need to create custom template filter `dict_get` to access dictionary in Django templates.

**Create template filter** in `scanner/templatetags/options_extras.py`:

```python
@register.filter
def dict_get(dictionary, key):
    """
    Get value from dictionary by key in template.
    
    Usage: {{ my_dict|dict_get:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
```

### Step 2: Add badge to accordion headers (stock-level status)

Add badge to accordion button showing overall stock status.

**File to modify**: `templates/scanner/partials/options_results.html`

**Find the accordion header**:
```html
<h2 class="accordion-header" id="heading{{ forloop.counter }}">
  <button class="accordion-button collapsed" ...>
    {{ symbol }} Options
  </button>
</h2>
```

**Add stock-level badge logic**:
```django
<h2 class="accordion-header" id="heading{{ forloop.counter }}">
  <button class="accordion-button collapsed" ...>
    {% with stock=curated_stocks|dict_get:symbol %}
      {% if stock %}
        {% with iv=stock.get_effective_intrinsic_value %}
          {% if iv is None %}
            <span class="badge bg-warning me-2">⚠</span>
          {% else %}
            {# Check if ANY option has strike <= IV #}
            {% with has_good_option=False %}
              {% for option in option_list %}
                {% if option.strike <= iv %}
                  {% with has_good_option=True %}{% endwith %}
                {% endif %}
              {% endfor %}
              
              {# Display appropriate badge #}
              {% if has_good_option %}
                <span class="badge bg-success me-2">✓</span>
              {% else %}
                <span class="badge bg-danger me-2">✗</span>
              {% endif %}
            {% endwith %}
          {% endif %}
        {% endwith %}
      {% else %}
        <span class="badge bg-secondary me-2">-</span>
      {% endif %}
    {% endwith %}
    {{ symbol }} Options
  </button>
</h2>
```

**Note**: Django template variables can't be reassigned. Need to use custom template tag instead.

**Create custom template tag** in `scanner/templatetags/options_extras.py`:

```python
@register.simple_tag
def check_good_options(option_list, intrinsic_value):
    """
    Check if any option in the list has strike <= intrinsic value.
    
    Args:
        option_list: List of option dictionaries
        intrinsic_value: Decimal intrinsic value or None
    
    Returns:
        bool: True if at least one option has strike <= IV
    """
    if intrinsic_value is None:
        return False
    
    for option in option_list:
        if option.get('strike', float('inf')) <= intrinsic_value:
            return True
    
    return False
```

**Updated accordion header template**:
```django
<h2 class="accordion-header" id="heading{{ forloop.counter }}">
  <button class="accordion-button collapsed" ...>
    {% with stock=curated_stocks|dict_get:symbol %}
      {% if stock %}
        {% with iv=stock.get_effective_intrinsic_value %}
          {% if iv is None %}
            <span class="badge bg-warning me-2">⚠</span>
          {% else %}
            {% check_good_options option_list iv as has_good_option %}
            {% if has_good_option %}
              <span class="badge bg-success me-2">✓</span>
            {% else %}
              <span class="badge bg-danger me-2">✗</span>
            {% endif %}
          {% endif %}
        {% endwith %}
      {% else %}
        <span class="badge bg-secondary me-2">-</span>
      {% endif %}
    {% endwith %}
    {{ symbol }} Options
  </button>
</h2>
```

### Step 3: Add custom CSS for badge alignment (if needed)

Test the layout and add custom CSS if badges need better alignment.

**File to modify**: `static/css/styles.css` (only if needed)

**Potential CSS additions**:
```css
/* Align badge vertically in table cells */
.table td .badge {
    vertical-align: middle;
}

/* Ensure badge doesn't wrap in accordion button */
.accordion-button .badge {
    flex-shrink: 0;
}

/* Add spacing between badge and text */
.accordion-button .badge {
    margin-right: 0.5rem;
}
```

**Test without CSS first** - Bootstrap's default badge styling may be sufficient.

### Step 4: Test visual indicators with various stock states

Test the badges display correctly in different scenarios.

**Test scenarios**:

1. **Stock with options below IV**:
   - Stock: AAPL, IV: $150
   - Options: Strike $140, $145, $155
   - Expected: 
     - Row 1: Green "✓ Good" (140 ≤ 150)
     - Row 2: Green "✓ Good" (145 ≤ 150)
     - Row 3: Red "✗ High" (155 > 150)
     - Header: Green "✓" (has at least one good option)

2. **Stock with all options above IV**:
   - Stock: TSLA, IV: $100
   - Options: Strike $105, $110, $115
   - Expected:
     - All rows: Red "✗ High"
     - Header: Red "✗" (no good options)

3. **Stock with NULL intrinsic value**:
   - Stock: ABNB, IV: NULL
   - Options: Any strikes
   - Expected:
     - All rows: Yellow "⚠ N/A"
     - Header: Yellow "⚠" (no valuation)

4. **Stock not in curated list** (edge case):
   - Stock: RANDOM, not in CuratedStock table
   - Options: Any strikes
   - Expected:
     - All rows: Gray "-" badge
     - Header: Gray "-" badge

**Manual testing checklist**:

- [ ] Run a scan that finds options
- [ ] Verify accordion headers show correct badges
- [ ] Expand accordions and check individual option badges
- [ ] Test with stock having NULL IV (set manually in admin)
- [ ] Test with stock having mix of strikes above/below IV
- [ ] Check responsive layout on mobile
- [ ] Verify badges don't break accordion collapse functionality

**Setup test data**:
```bash
# Django shell
just exec python manage.py shell
```

```python
from scanner.models import CuratedStock

# Set up test stocks with different IV states
stock1 = CuratedStock.objects.get(symbol='AAPL')
stock1.intrinsic_value = 150.00
stock1.preferred_valuation_method = 'eps'
stock1.save()

stock2 = CuratedStock.objects.get(symbol='TSLA')
stock2.intrinsic_value = None
stock2.intrinsic_value_fcf = None
stock2.save()

# Run scan and verify badges
```

## Acceptance Criteria

### Badge Display Requirements

- [ ] Green "✓ Good" badge shown for options with strike ≤ IV
- [ ] Red "✗ High" badge shown for options with strike > IV
- [ ] Yellow "⚠ N/A" badge shown when IV is NULL
- [ ] Gray "-" badge shown for non-curated stocks (edge case)
- [ ] All badges use Bootstrap badge component

### Accordion Header Requirements

- [ ] Green "✓" badge shown when at least one option has strike ≤ IV
- [ ] Red "✗" badge shown when all options have strike > IV
- [ ] Yellow "⚠" badge shown when IV is NULL
- [ ] Badge appears at beginning of accordion button text
- [ ] Badge doesn't break accordion collapse/expand functionality

### Table Layout Requirements

- [ ] New "Status" column added as first column in table
- [ ] Badge fits properly in table cell
- [ ] Table remains responsive on mobile devices
- [ ] Badge doesn't cause horizontal scrolling

### Template Filter Requirements

- [ ] `dict_get` filter works correctly for dictionary access
- [ ] `check_good_options` template tag correctly identifies good options
- [ ] Template tags handle None values gracefully
- [ ] Template tags are registered in `options_extras.py`

### Visual/UX Requirements

- [ ] Badges are visually clear and easy to understand
- [ ] Color coding is consistent (green=good, red=bad, yellow=warning)
- [ ] Layout doesn't break with badges added
- [ ] Spacing around badges is appropriate
- [ ] Badges align properly in table cells

## Files Involved

### Modified Files

- `templates/scanner/partials/options_results.html`
  - Add "Status" column header
  - Add badge to each option row
  - Add badge to accordion headers
  
- `scanner/templatetags/options_extras.py`
  - Add `dict_get` filter for dictionary access
  - Add `check_good_options` template tag for stock-level status

### Potentially Modified Files

- `static/css/styles.css` (only if default Bootstrap styling insufficient)

## Notes

### Django Template Limitations

**Can't reassign variables**:
Django templates don't allow variable reassignment, which is why we need a custom template tag for `check_good_options`.

**Dictionary access**:
Django templates can't use Python's `dict[key]` syntax, so we need the `dict_get` filter.

### Bootstrap Badge Classes

**Available classes**:
- `badge bg-success` - Green background
- `badge bg-danger` - Red background
- `badge bg-warning` - Yellow background
- `badge bg-secondary` - Gray background

**Utility classes**:
- `me-2` - Margin end (right) of 0.5rem
- `ms-2` - Margin start (left) of 0.5rem

### Comparison Logic

**Strike vs IV comparison**:
```python
if option.strike <= intrinsic_value:
    # Good - option strike at or below fair value
    # Selling put at this strike means getting paid to potentially buy below fair value
```

**Important**: For PUT options (wheel strategy):
- Strike ≤ IV = Good (would buy stock below/at fair value if assigned)
- Strike > IV = Risky (would buy stock above fair value if assigned)

### Accessibility Considerations

**Color alone is not enough**:
- We use symbols (✓, ✗, ⚠) in addition to colors
- Screen readers will read badge text

**Future enhancement** (optional):
- Add `title` attribute to badges for tooltips
- Example: `<span class="badge bg-success" title="Strike price is at or below intrinsic value">✓ Good</span>`

### Performance

**Template rendering**:
- Dictionary lookups: O(1)
- Check good options: O(n) where n = options per stock
- Typical: 3-5 options per stock, negligible overhead

**No database queries**:
- All data already in context from Task 024
- Pure template rendering logic

## Dependencies

- Requires Task 024 (intrinsic value context in views)
- Uses `CuratedStock.get_effective_intrinsic_value()` method
- Requires Bootstrap 5 (already in project)

## Reference

**Bootstrap Badges**:
- https://getbootstrap.com/docs/5.0/components/badge/

**Django Template Tags**:
- Custom filters: https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#writing-custom-template-filters
- Custom tags: https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#simple-tags

**Django Template Language**:
- https://docs.djangoproject.com/en/5.1/ref/templates/language/
