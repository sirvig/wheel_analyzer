# Task 013: Add Intrinsic Value Fields to CuratedStock Model

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add database fields to CuratedStock model
- [x] Step 2: Create and run Django migration
- [x] Step 3: Update Django admin interface
- [x] Step 4: Test model changes

### Summary of Changes:
- Added 7 new fields to CuratedStock model (2 calculation results, 5 DCF assumptions)
- Generated and applied migration `0004_add_intrinsic_value_fields.py`
- Updated Django admin interface with organized fieldsets
- Calculation result fields (intrinsic_value, last_calculation_date) set as read-only
- DCF assumption fields editable with sensible defaults
- All existing tests continue to pass

## Overview

This task adds database fields to the `CuratedStock` model to store intrinsic value calculations and the DCF (Discounted Cash Flow) assumptions used to calculate them. This is the foundation for Phase 4's stock valuation feature, which will calculate fair value for stocks in the curated list on a weekly basis.

The fields will store:
- **Calculation results**: intrinsic value and when it was last calculated
- **DCF assumptions**: current EPS, growth rates, desired return, and other parameters used in the calculation

These assumptions will be manually editable in the Django admin interface, allowing customization per stock.

## Implementation Steps

### Step 1: Add database fields to CuratedStock model

Open `scanner/models.py` and add the following fields to the `CuratedStock` model:

**Calculation Result Fields:**
- `intrinsic_value` - The calculated fair value per share (DecimalField)
- `last_calculation_date` - Timestamp of last calculation (DateTimeField)

**DCF Assumption Fields (manually editable):**
- `current_eps` - Current Earnings Per Share (DecimalField)
- `eps_growth_rate` - Expected EPS growth rate percentage (DecimalField, default=10.0)
- `eps_multiple` - Multiple applied to terminal year EPS (DecimalField, default=20.0)
- `desired_return` - Desired annual return percentage (DecimalField, default=15.0)
- `projection_years` - Number of years to project (IntegerField, default=5)

**Files to modify:**
- `scanner/models.py`

**Field specifications:**
```python
# Calculation Results (auto-populated by calculation command)
intrinsic_value = models.DecimalField(
    max_digits=10, 
    decimal_places=2, 
    null=True, 
    blank=True,
    help_text="Calculated fair value per share based on DCF model"
)
last_calculation_date = models.DateTimeField(
    null=True, 
    blank=True,
    help_text="When the intrinsic value was last calculated"
)

# DCF Assumptions (manually editable in admin)
current_eps = models.DecimalField(
    max_digits=10, 
    decimal_places=2, 
    null=True, 
    blank=True,
    help_text="Current Earnings Per Share (fetched from Alpha Vantage)"
)
eps_growth_rate = models.DecimalField(
    max_digits=5, 
    decimal_places=2, 
    default=10.0,
    help_text="Expected EPS growth rate (%)"
)
eps_multiple = models.DecimalField(
    max_digits=5, 
    decimal_places=2, 
    default=20.0,
    help_text="Multiple applied to terminal year EPS for terminal value"
)
desired_return = models.DecimalField(
    max_digits=5, 
    decimal_places=2, 
    default=15.0,
    help_text="Desired annual return rate (%) - used as discount rate"
)
projection_years = models.IntegerField(
    default=5,
    help_text="Number of years to project EPS growth"
)
```

### Step 2: Create and run Django migration

Generate and apply the database migration for the new fields:

**Commands to run:**
```bash
# Generate migration file
just exec python manage.py makemigrations scanner --name add_intrinsic_value_fields

# Review the generated migration file
# Located at: scanner/migrations/000X_add_intrinsic_value_fields.py

# Apply migration to database
just exec python manage.py migrate scanner
```

**Files created:**
- `scanner/migrations/000X_add_intrinsic_value_fields.py`

**Verification:**
- Check that migration file was created successfully
- Review migration operations (should be AddField for each new field)
- Verify migration applies without errors
- Confirm fields exist in database (via `just dbconsole` or admin)

### Step 3: Update Django admin interface

Update the `CuratedStockAdmin` class in `scanner/admin.py` to display the new fields:

**Display organization:**
- Show calculation results as **read-only** fields (users shouldn't manually edit these)
- Show DCF assumptions as **editable** fields (users can customize per stock)
- Group related fields together for better UX

**Files to modify:**
- `scanner/admin.py`

**Admin configuration to add:**
```python
@admin.register(CuratedStock)
class CuratedStockAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 
        'active', 
        'intrinsic_value',  # NEW
        'last_calculation_date',  # NEW
        'created_at'
    ]
    list_filter = ['active', 'created_at']
    search_fields = ['symbol', 'notes']
    readonly_fields = [
        'intrinsic_value',  # NEW - auto-calculated, should not be manually edited
        'last_calculation_date',  # NEW - auto-set by command
        'created_at', 
        'updated_at'
    ]
    
    fieldsets = (
        ('Stock Information', {
            'fields': ('symbol', 'active', 'notes')
        }),
        ('Intrinsic Value Calculation', {
            'fields': ('intrinsic_value', 'last_calculation_date'),
            'description': 'Calculated values updated by weekly valuation job'
        }),
        ('DCF Assumptions', {
            'fields': (
                'current_eps',
                'eps_growth_rate',
                'eps_multiple',
                'desired_return',
                'projection_years'
            ),
            'description': 'Customize DCF model assumptions for this stock'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # Collapsible section
        }),
    )
```

### Step 4: Test model changes

Verify the model changes work correctly:

**Testing checklist:**
- [ ] Migration applies successfully without errors
- [ ] New fields appear in Django admin for CuratedStock
- [ ] Calculation result fields are read-only in admin
- [ ] DCF assumption fields are editable in admin
- [ ] Default values are set correctly for new stocks
- [ ] Help text is visible for each field
- [ ] Existing CuratedStock records still load correctly
- [ ] Can edit and save DCF assumptions via admin
- [ ] Field validation works (e.g., decimal places, max digits)

**Manual testing steps:**
1. Start development server: `just run`
2. Navigate to admin: `http://localhost:8000/admin/scanner/curatedstock/`
3. Open an existing stock (e.g., AAPL)
4. Verify all new fields are visible
5. Verify calculation fields show as read-only (grayed out)
6. Edit DCF assumption fields (e.g., change eps_growth_rate to 12.0)
7. Save and verify changes persist
8. Create a new stock entry and verify defaults are set

## Acceptance Criteria

### Database Schema:
- [ ] CuratedStock model has 7 new fields (2 calculation results, 5 DCF assumptions)
- [ ] All fields have appropriate data types (DecimalField, IntegerField, DateTimeField)
- [ ] Default values are set correctly (eps_growth_rate=10, eps_multiple=20, desired_return=15, projection_years=5)
- [ ] Fields allow NULL/blank where appropriate (intrinsic_value, last_calculation_date, current_eps)
- [ ] Help text is clear and informative for each field

### Django Admin:
- [ ] Intrinsic value fields are visible in admin interface
- [ ] Calculation result fields (intrinsic_value, last_calculation_date) are read-only
- [ ] DCF assumption fields are editable
- [ ] Fields are organized into logical fieldsets
- [ ] List display shows symbol, active status, intrinsic_value, and last_calculation_date
- [ ] Help text displays correctly in admin interface

### Data Integrity:
- [ ] Migration runs successfully without errors
- [ ] Existing CuratedStock records are preserved
- [ ] New stocks get correct default values
- [ ] Field validation works (decimal precision, required fields)
- [ ] Can save and retrieve values correctly

## Files Involved

### Modified Files:
- `scanner/models.py` - Add fields to CuratedStock model
- `scanner/admin.py` - Update CuratedStockAdmin configuration

### Created Files:
- `scanner/migrations/000X_add_intrinsic_value_fields.py` - Django migration

### Files to Review:
- Existing migrations to understand numbering scheme
- Current admin configuration for consistency

## Notes

### DCF Model Explained:
The Discounted Cash Flow (DCF) model calculates intrinsic value by:
1. Projecting future EPS for 5 years using growth rate
2. Calculating terminal value (Year 5 EPS × multiple)
3. Discounting all values to present using desired return rate
4. Summing present values to get intrinsic value per share

### Field Design Decisions:
- **DecimalField precision**: max_digits=10, decimal_places=2 for currency/price values
- **NULL allowed**: intrinsic_value, last_calculation_date, current_eps can be NULL initially
- **Defaults provided**: For DCF assumptions to ensure calculation can run immediately
- **Read-only in admin**: Prevents manual corruption of calculated values

### Future Enhancements:
- Task 014 will create the calculation logic
- Task 015 will create the management command to populate these fields
- Phase 5 will use intrinsic_value to provide visual indicators in options scanner

### Alpha Vantage API:
The `current_eps` field will be populated by fetching from:
```
https://www.alphavantage.co/query?function=OVERVIEW&symbol=SYMBOL&apikey=API_KEY
```
Response field: `"EPS": "6.42"`

### Database Backup:
Before running migration in production:
```bash
just backup
```

## Testing Checklist

### Migration Tests:
- [ ] `makemigrations` generates migration file without warnings
- [ ] Migration file includes all 7 new fields
- [ ] `migrate` applies successfully without errors
- [ ] `showmigrations` shows migration as applied
- [ ] Database schema matches model definition (verify via dbconsole)

### Admin Interface Tests:
- [ ] Admin page loads without errors
- [ ] All new fields are visible in the form
- [ ] Fieldsets organize fields logically
- [ ] Read-only fields cannot be edited
- [ ] Editable fields accept valid input
- [ ] Help text displays on hover/click
- [ ] Form validation works correctly

### Data Tests:
- [ ] Existing stocks load correctly with NULL values for new fields
- [ ] New stocks get correct default values
- [ ] Can update DCF assumptions and save
- [ ] Changes persist after page reload
- [ ] Field validation prevents invalid data (e.g., negative values if constrained)

### Integration Tests:
- [ ] Other parts of the application still work (scanner, tracker)
- [ ] No breaking changes to existing functionality
- [ ] Tests pass: `just test scanner/tests/test_scanner_models.py`

## Reference

**Model field documentation:**
- DecimalField: https://docs.djangoproject.com/en/5.1/ref/models/fields/#decimalfield
- DateTimeField: https://docs.djangoproject.com/en/5.1/ref/models/fields/#datetimefield
- IntegerField: https://docs.djangoproject.com/en/5.1/ref/models/fields/#integerfield

**Admin customization:**
- Fieldsets: https://docs.djangoproject.com/en/5.1/ref/contrib/admin/#django.contrib.admin.ModelAdmin.fieldsets
- Read-only fields: https://docs.djangoproject.com/en/5.1/ref/contrib/admin/#django.contrib.admin.ModelAdmin.readonly_fields

**Migration commands:**
- makemigrations: https://docs.djangoproject.com/en/5.1/ref/django-admin/#makemigrations
- migrate: https://docs.djangoproject.com/en/5.1/ref/django-admin/#migrate
