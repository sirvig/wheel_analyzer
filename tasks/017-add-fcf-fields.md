# Task 017: Add FCF Fields to CuratedStock Model

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add FCF database fields to CuratedStock model
- [x] Step 2: Create and run Django migration
- [x] Step 3: Update Django admin interface
- [x] Step 4: Test model changes

### Summary of Changes

- Added 5 new fields to CuratedStock model:
  - `intrinsic_value_fcf` - FCF-based intrinsic value (read-only)
  - `current_fcf_per_share` - TTM FCF per share (read-only)
  - `fcf_growth_rate` - FCF growth rate assumption (default: 10%, editable)
  - `fcf_multiple` - FCF terminal value multiple (default: 20, editable)
  - `preferred_valuation_method` - Choice between EPS/FCF (default: "EPS", editable)
- Generated and applied migration `0005_add_fcf_fields.py`
- Updated Django admin with organized fieldsets:
  - Separated EPS and FCF assumption sections
  - Added both intrinsic values to list display
  - Added preferred method to list display and list filter
  - Made FCF calculation results read-only
- Django system check passes with no issues

## Overview

This task adds Free Cash Flow (FCF) based valuation fields to the `CuratedStock` model. This enables dual valuation approach where stocks can be valued using both EPS-based and FCF-based DCF methods, with users choosing their preferred method per stock.

The enhancement will allow users to:
- Calculate intrinsic value using both EPS and FCF methods
- Store both valuation results independently
- Choose which valuation method to display as primary per stock
- Customize FCF-specific DCF assumptions

## Implementation Steps

### Step 1: Add FCF database fields to CuratedStock model

Open `scanner/models.py` and add the following fields to the `CuratedStock` model:

**FCF Calculation Results:**
- `intrinsic_value_fcf` - FCF-based intrinsic value (DecimalField)
- `current_fcf_per_share` - TTM Free Cash Flow per share (DecimalField)

**FCF DCF Assumptions:**
- `fcf_growth_rate` - FCF growth rate percentage (DecimalField, default=10.0)
- `fcf_multiple` - Multiple for FCF terminal value (DecimalField, default=20.0)

**Display Preference:**
- `preferred_valuation_method` - Choice between 'EPS' or 'FCF' (CharField)

**Files to modify:**
- `scanner/models.py`

**Field specifications:**
```python
# FCF Calculation Results (auto-populated by calculation command)
intrinsic_value_fcf = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True,
    help_text="Calculated fair value per share based on FCF DCF model",
)
current_fcf_per_share = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True,
    help_text="Trailing twelve months Free Cash Flow per share",
)

# FCF DCF Assumptions (manually editable in admin)
fcf_growth_rate = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    default=10.0,
    help_text="Expected FCF growth rate (%)",
)
fcf_multiple = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    default=20.0,
    help_text="Multiple applied to terminal year FCF for terminal value",
)

# Valuation Display Preference
preferred_valuation_method = models.CharField(
    max_length=3,
    choices=[
        ("EPS", "EPS-based"),
        ("FCF", "FCF-based"),
    ],
    default="EPS",
    help_text="Preferred valuation method to display",
)
```

### Step 2: Create and run Django migration

Generate and apply the database migration for the new fields:

**Commands to run:**
```bash
# Generate migration file
uv run python manage.py makemigrations scanner --name add_fcf_fields

# Review the generated migration file
# Located at: scanner/migrations/000X_add_fcf_fields.py

# Apply migration to database
uv run python manage.py migrate scanner
```

**Files created:**
- `scanner/migrations/000X_add_fcf_fields.py`

**Verification:**
- Check that migration file was created successfully
- Review migration operations (should be AddField for each new field)
- Verify migration applies without errors
- Confirm fields exist in database

### Step 3: Update Django admin interface

Update the `CuratedStockAdmin` class in `scanner/admin.py` to display the new FCF fields:

**Display organization:**
- Add new fieldset "FCF-based DCF Assumptions" for FCF parameters
- Add intrinsic_value_fcf to "Intrinsic Value Calculation" fieldset
- Add preferred_valuation_method to "Intrinsic Value Display" section
- Show both intrinsic values in list_display
- Make FCF calculation results read-only

**Files to modify:**
- `scanner/admin.py`

**Admin configuration updates:**
```python
@admin.register(CuratedStock)
class CuratedStockAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "active",
        "intrinsic_value",
        "intrinsic_value_fcf",
        "preferred_valuation_method",
        "last_calculation_date",
        "created_at",
    ]
    
    readonly_fields = [
        "intrinsic_value",
        "intrinsic_value_fcf",  # NEW
        "current_fcf_per_share",  # NEW
        "last_calculation_date",
        "created_at",
        "updated_at",
    ]
    
    fieldsets = (
        ("Stock Information", {"fields": ("symbol", "active", "notes")}),
        (
            "Intrinsic Value Calculation",
            {
                "fields": (
                    "intrinsic_value",
                    "intrinsic_value_fcf",  # NEW
                    "preferred_valuation_method",  # NEW
                    "last_calculation_date",
                ),
                "description": "Calculated values updated by weekly valuation job",
            },
        ),
        (
            "EPS-based DCF Assumptions",
            {
                "fields": (
                    "current_eps",
                    "eps_growth_rate",
                    "eps_multiple",
                    "desired_return",
                    "projection_years",
                ),
                "description": "Customize EPS-based DCF model assumptions for this stock",
            },
        ),
        (
            "FCF-based DCF Assumptions",  # NEW FIELDSET
            {
                "fields": (
                    "current_fcf_per_share",
                    "fcf_growth_rate",
                    "fcf_multiple",
                ),
                "description": "Customize FCF-based DCF model assumptions for this stock",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
```

### Step 4: Test model changes

Verify the model changes work correctly:

**Testing checklist:**
- [ ] Migration applies successfully without errors
- [ ] New FCF fields appear in Django admin for CuratedStock
- [ ] FCF calculation result fields are read-only in admin
- [ ] FCF assumption fields are editable in admin
- [ ] Default values are set correctly for new stocks
- [ ] preferred_valuation_method dropdown shows EPS/FCF options
- [ ] Help text is visible for each field
- [ ] Existing CuratedStock records still load correctly
- [ ] Can edit and save FCF assumptions via admin
- [ ] Field validation works (e.g., decimal places, max digits)

**Manual testing steps:**
1. Start development server: `just run`
2. Navigate to admin: `http://localhost:8000/admin/scanner/curatedstock/`
3. Open an existing stock (e.g., AAPL)
4. Verify all new FCF fields are visible
5. Verify FCF calculation fields show as read-only (grayed out)
6. Edit FCF assumption fields (e.g., change fcf_growth_rate to 12.0)
7. Save and verify changes persist
8. Create a new stock entry and verify defaults are set

## Acceptance Criteria

### Database Schema:
- [ ] CuratedStock model has 5 new fields (2 calculation results, 2 FCF assumptions, 1 preference)
- [ ] All fields have appropriate data types (DecimalField, CharField)
- [ ] Default values are set correctly (fcf_growth_rate=10, fcf_multiple=20, preferred_valuation_method='EPS')
- [ ] Fields allow NULL/blank where appropriate (intrinsic_value_fcf, current_fcf_per_share)
- [ ] Help text is clear and informative for each field

### Django Admin:
- [ ] FCF fields are visible in admin interface
- [ ] FCF calculation result fields are read-only
- [ ] FCF assumption fields are editable
- [ ] Fields are organized into logical fieldsets (separate EPS and FCF sections)
- [ ] List display shows both intrinsic values and preferred method
- [ ] Help text displays correctly in admin interface
- [ ] preferred_valuation_method dropdown works correctly

### Data Integrity:
- [ ] Migration runs successfully without errors
- [ ] Existing CuratedStock records are preserved
- [ ] New stocks get correct default values
- [ ] Field validation works (decimal precision, required fields)
- [ ] Can save and retrieve values correctly
- [ ] Both valuation methods can coexist

## Files Involved

### Modified Files:
- `scanner/models.py` - Add FCF fields to CuratedStock model
- `scanner/admin.py` - Update CuratedStockAdmin configuration

### Created Files:
- `scanner/migrations/000X_add_fcf_fields.py` - Django migration

### Files to Review:
- Existing migrations to understand numbering scheme
- Current admin configuration for consistency

## Notes

### FCF vs EPS Valuation:

**EPS-based DCF** (existing):
- Uses earnings per share as cash flow proxy
- Simpler, widely used metric
- Available for most companies
- May not reflect actual cash generation

**FCF-based DCF** (new):
- Uses actual free cash flow per share
- More accurate representation of cash generation
- Better for cash-intensive or capital-heavy businesses
- Requires more data (quarterly cash flow statements)

### Dual Valuation Approach:

The system will calculate both methods independently:
1. **EPS valuation**: Uses current_eps, eps_growth_rate, eps_multiple
2. **FCF valuation**: Uses current_fcf_per_share, fcf_growth_rate, fcf_multiple
3. Both share: desired_return (discount rate), projection_years

Users can:
- View both valuations side-by-side in admin
- Choose preferred method per stock for display
- Compare results between methods

### Field Design Decisions:
- **Separate fields**: FCF and EPS fields are separate to allow independent configuration
- **Same defaults**: FCF growth rate and multiple default to same values as EPS for consistency
- **Shared parameters**: desired_return and projection_years are shared between both methods
- **NULL allowed**: Calculation results can be NULL initially or if calculation fails
- **Read-only in admin**: Prevents manual corruption of calculated values

### Future Enhancements:
- Task 018 will create FCF calculation logic
- Task 019 will update management command to calculate both methods
- Phase 5 will use preferred_valuation_method to display appropriate value in scanner

### Database Backup:
Before running migration in production:
```bash
just backup
```

## Testing Checklist

### Migration Tests:
- [ ] `makemigrations` generates migration file without warnings
- [ ] Migration file includes all 5 new fields
- [ ] `migrate` applies successfully without errors
- [ ] `showmigrations` shows migration as applied
- [ ] Database schema matches model definition

### Admin Interface Tests:
- [ ] Admin page loads without errors
- [ ] All new fields are visible in the form
- [ ] Fieldsets organize fields logically (separate EPS and FCF)
- [ ] Read-only fields cannot be edited
- [ ] Editable fields accept valid input
- [ ] Help text displays on hover/click
- [ ] Form validation works correctly

### Data Tests:
- [ ] Existing stocks load correctly with NULL values for new fields
- [ ] New stocks get correct default values
- [ ] Can update FCF assumptions and save
- [ ] Changes persist after page reload
- [ ] Both intrinsic values can be NULL or have different values

### Integration Tests:
- [ ] Other parts of the application still work (scanner, tracker)
- [ ] No breaking changes to existing functionality
- [ ] Tests pass: `just test scanner/tests/test_scanner_models.py`

## Reference

**Model field documentation:**
- DecimalField: https://docs.djangoproject.com/en/5.1/ref/models/fields/#decimalfield
- CharField: https://docs.djangoproject.com/en/5.1/ref/models/fields/#charfield

**Admin customization:**
- Fieldsets: https://docs.djangoproject.com/en/5.1/ref/contrib/admin/#django.contrib.admin.ModelAdmin.fieldsets
- Read-only fields: https://docs.djangoproject.com/en/5.1/ref/contrib/admin/#django.contrib.admin.ModelAdmin.readonly_fields

**Migration commands:**
- makemigrations: https://docs.djangoproject.com/en/5.1/ref/django-admin/#makemigrations
- migrate: https://docs.djangoproject.com/en/5.1/ref/django-admin/#migrate
