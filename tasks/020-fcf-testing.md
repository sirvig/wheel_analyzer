# Task 020: Add FCF Testing

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Extend unit tests for FCF calculations
- [x] Step 2: Add integration tests for FCF command

### Summary of Changes

- Added 8 new integration test cases to `scanner/tests/test_calculate_intrinsic_value.py`:
  - Test dual EPS and FCF calculation success
  - Test FCF skipped with insufficient quarterly data
  - Test FCF skipped with negative FCF (but current_fcf_per_share is still saved)
  - Test CASH_FLOW data is cached properly
  - Test command summary shows both EPS and FCF statistics
  - Test last_calculation_date is updated for either method
  - Test preferred_valuation_method persists through calculation
  - Test only active stocks get FCF calculations
- Updated management command to save current_fcf_per_share even when negative
- All 8 FCF integration tests pass
- Total test suite: 56 unit tests + 32 existing integration tests + 8 new FCF integration tests = 96 tests passing

## Overview

This task adds comprehensive testing for the FCF-based valuation feature. While basic unit tests were created in Task 018, this task extends test coverage to include integration tests for the management command and ensures the dual EPS/FCF calculation system works correctly end-to-end.

The goal is to achieve >90% test coverage for all FCF-related code and ensure robust error handling.

## Implementation Steps

### Step 1: Extend unit tests for FCF calculations

Extend `scanner/tests/test_valuation.py` with additional edge cases:

**Additional test cases to add:**

```python
class TestCalculateFCFFromQuartersEdgeCases:
    """Additional edge cases for FCF quarterly calculation."""
    
    def test_calculate_fcf_with_extra_quarters(self):
        """Test that only most recent 4 quarters are used."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "10000000000", "capitalExpenditures": "-2000000000"},
                {"operatingCashflow": "11000000000", "capitalExpenditures": "-2100000000"},
                {"operatingCashflow": "10500000000", "capitalExpenditures": "-1900000000"},
                {"operatingCashflow": "12000000000", "capitalExpenditures": "-2200000000"},
                {"operatingCashflow": "9000000000", "capitalExpenditures": "-1800000000"},  # 5th quarter - should be ignored
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Should use first 4 quarters only
        assert result == Decimal("51700000000.00")
    
    def test_calculate_fcf_string_numbers(self):
        """Test handling of string-formatted numbers."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "10000000000.50", "capitalExpenditures": "-2000000000.25"},
                {"operatingCashflow": "11000000000.75", "capitalExpenditures": "-2100000000.50"},
                {"operatingCashflow": "10500000000.25", "capitalExpenditures": "-1900000000.75"},
                {"operatingCashflow": "12000000000.00", "capitalExpenditures": "-2200000000.00"},
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Should handle decimal strings correctly
        assert result > Decimal("51700000000")
    
    def test_calculate_fcf_very_large_numbers(self):
        """Test with very large cash flow numbers."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "100000000000", "capitalExpenditures": "-20000000000"},
                {"operatingCashflow": "110000000000", "capitalExpenditures": "-21000000000"},
                {"operatingCashflow": "105000000000", "capitalExpenditures": "-19000000000"},
                {"operatingCashflow": "120000000000", "capitalExpenditures": "-22000000000"},
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        assert result > Decimal("0")
        assert result == result.quantize(Decimal("0.01"))


class TestCalculateIntrinsicValueFCFEdgeCases:
    """Additional edge cases for FCF-based intrinsic value."""
    
    def test_intrinsic_value_fcf_very_low_fcf(self):
        """Test with very low FCF per share."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("0.01"),
            fcf_growth_rate=Decimal("5.0"),
            fcf_multiple=Decimal("15.0"),
            desired_return=Decimal("12.0"),
            projection_years=5,
        )
        assert result["intrinsic_value"] > Decimal("0")
        assert result["intrinsic_value"] < Decimal("1.00")
    
    def test_intrinsic_value_fcf_high_growth(self):
        """Test with high FCF growth rate."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("3.00"),
            fcf_growth_rate=Decimal("30.0"),  # High growth
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )
        # High growth should result in high intrinsic value
        assert result["intrinsic_value"] > Decimal("100.00")
    
    def test_intrinsic_value_fcf_vs_eps_comparison(self):
        """Test that FCF and EPS methods produce reasonable results."""
        # Same inputs for both methods
        current_value = Decimal("5.00")
        growth = Decimal("10.0")
        multiple = Decimal("20.0")
        discount = Decimal("15.0")
        years = 5
        
        eps_result = calculate_intrinsic_value(
            current_eps=current_value,
            eps_growth_rate=growth,
            eps_multiple=multiple,
            desired_return=discount,
            projection_years=years,
        )
        
        fcf_result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=current_value,
            fcf_growth_rate=growth,
            fcf_multiple=multiple,
            desired_return=discount,
            projection_years=years,
        )
        
        # With same inputs, should produce same results
        assert eps_result["intrinsic_value"] == fcf_result["intrinsic_value"]
```

### Step 2: Add integration tests for FCF command

Extend `scanner/tests/test_calculate_intrinsic_value.py` with FCF-specific tests:

**New test cases to add:**

```python
@pytest.mark.django_db
class TestCalculateIntrinsicValueFCFIntegration:
    """Integration tests for FCF calculations in management command."""
    
    @pytest.fixture
    def mock_alpha_vantage_dual(self):
        """Mock both OVERVIEW and CASH_FLOW API responses."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            def side_effect(url):
                if "OVERVIEW" in url:
                    return {
                        "Symbol": "AAPL",
                        "EPS": "6.42",
                        "SharesOutstanding": "15000000000",
                    }
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect
            yield mock
    
    def test_command_calculates_both_eps_and_fcf(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that command calculates both EPS and FCF intrinsic values."""
        stock = CuratedStockFactory(symbol="AAPL", active=True)
        
        call_command("calculate_intrinsic_value")
        
        stock.refresh_from_db()
        
        # Both values should be calculated
        assert stock.intrinsic_value is not None
        assert stock.intrinsic_value_fcf is not None
        assert stock.current_eps is not None
        assert stock.current_fcf_per_share is not None
    
    def test_command_fcf_skipped_with_insufficient_quarters(
        self, mock_alpha_vantage, mock_sleep
    ):
        """Test that FCF is skipped when fewer than 4 quarters available."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            def side_effect(url):
                if "OVERVIEW" in url:
                    return {"Symbol": "AAPL", "EPS": "6.42", "SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect
            
            stock = CuratedStockFactory(symbol="AAPL", active=True)
            call_command("calculate_intrinsic_value")
            
            stock.refresh_from_db()
            
            # EPS should succeed
            assert stock.intrinsic_value is not None
            # FCF should be skipped
            assert stock.intrinsic_value_fcf is None
    
    def test_command_fcf_skipped_with_negative_fcf(
        self, mock_alpha_vantage, mock_sleep
    ):
        """Test that FCF is skipped when FCF per share is negative."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            def side_effect(url):
                if "OVERVIEW" in url:
                    return {"Symbol": "TSLA", "EPS": "3.50", "SharesOutstanding": "3000000000"}
                elif "CASH_FLOW" in url:
                    # Negative FCF scenario
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "1000000000", "capitalExpenditures": "-5000000000"},
                            {"operatingCashflow": "1100000000", "capitalExpenditures": "-5100000000"},
                            {"operatingCashflow": "1050000000", "capitalExpenditures": "-4900000000"},
                            {"operatingCashflow": "1200000000", "capitalExpenditures": "-5200000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect
            
            stock = CuratedStockFactory(symbol="TSLA", active=True)
            call_command("calculate_intrinsic_value")
            
            stock.refresh_from_db()
            
            # EPS should succeed
            assert stock.intrinsic_value is not None
            # FCF should be skipped (negative)
            assert stock.intrinsic_value_fcf is None
            # But FCF per share should still be calculated (for reference)
            assert stock.current_fcf_per_share is not None
            assert stock.current_fcf_per_share < Decimal("0")
    
    def test_command_eps_fails_fcf_succeeds(self, mock_alpha_vantage, mock_sleep):
        """Test that FCF can succeed even if EPS fails."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            def side_effect(url):
                if "OVERVIEW" in url:
                    # Missing EPS but has shares outstanding
                    return {"Symbol": "AAPL", "SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect
            
            stock = CuratedStockFactory(symbol="AAPL", active=True)
            call_command("calculate_intrinsic_value")
            
            stock.refresh_from_db()
            
            # EPS should fail (no value)
            assert stock.intrinsic_value is None
            # But FCF could potentially succeed if command is updated to handle this
            # (Current implementation may skip FCF if EPS fails - adjust based on final implementation)
    
    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_command_caches_cash_flow_data(
        self, mock_cache, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that CASH_FLOW API responses are cached."""
        mock_cache.get.return_value = None  # Cache miss
        
        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")
        
        # Verify cache was checked and set for both OVERVIEW and CASH_FLOW
        cache_calls = [call[0][0] for call in mock_cache.get.call_args_list]
        assert "av_overview_AAPL" in cache_calls
        assert "av_cashflow_AAPL" in cache_calls
        
        # Verify cache was set for both
        assert mock_cache.set.call_count >= 2
    
    def test_command_summary_shows_both_methods(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that command summary shows statistics for both methods."""
        CuratedStockFactory(symbol="AAPL", active=True)
        CuratedStockFactory(symbol="MSFT", active=True)
        
        out = StringIO()
        call_command("calculate_intrinsic_value", stdout=out)
        
        output = out.getvalue()
        
        # Verify summary includes both methods
        assert "EPS Method:" in output
        assert "FCF Method:" in output
        assert "Successful:" in output
    
    def test_command_updates_last_calculation_date_for_both(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that last_calculation_date is updated when either method runs."""
        stock = CuratedStockFactory(symbol="AAPL", active=True)
        
        before_time = timezone.now()
        call_command("calculate_intrinsic_value")
        after_time = timezone.now()
        
        stock.refresh_from_db()
        
        # Date should be updated
        assert stock.last_calculation_date is not None
        assert before_time <= stock.last_calculation_date <= after_time
    
    def test_command_preferred_valuation_method_persists(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that preferred_valuation_method setting is preserved."""
        stock = CuratedStockFactory(
            symbol="AAPL",
            active=True,
            preferred_valuation_method="FCF"
        )
        
        call_command("calculate_intrinsic_value")
        
        stock.refresh_from_db()
        
        # Preference should be unchanged
        assert stock.preferred_valuation_method == "FCF"
```

**Test count**: ~10-15 new integration test cases

## Acceptance Criteria

### Unit Test Coverage:
- [ ] Edge cases for FCF quarterly calculation covered
- [ ] Large numbers handled correctly
- [ ] String vs numeric formats tested
- [ ] FCF vs EPS comparison test passes
- [ ] All unit tests pass

### Integration Test Coverage:
- [ ] Dual calculation (EPS + FCF) tested
- [ ] Insufficient quarters handled
- [ ] Negative FCF handled
- [ ] Independent failures tested
- [ ] Cache behavior verified for both APIs
- [ ] Summary output format verified
- [ ] All integration tests pass

### Test Quality:
- [ ] Tests use appropriate mocks
- [ ] Tests are independent (can run in any order)
- [ ] Clear test descriptions
- [ ] Edge cases comprehensively covered

### Coverage Goals:
- [ ] FCF calculation functions: >95% coverage
- [ ] Command FCF processing: >90% coverage
- [ ] Overall valuation module: >90% coverage

## Files Involved

### Modified Files:
- `scanner/tests/test_valuation.py` - Add FCF unit tests
- `scanner/tests/test_calculate_intrinsic_value.py` - Add FCF integration tests

## Notes

### Testing Strategy:

**Unit Tests**:
- Test FCF calculation functions in isolation
- Verify mathematical accuracy
- Test edge cases and error conditions
- Fast execution, no external dependencies

**Integration Tests**:
- Test end-to-end command execution
- Mock both OVERVIEW and CASH_FLOW APIs
- Test dual calculation workflow
- Verify database updates
- Test error handling and recovery

### Key Test Scenarios:

1. **Both succeed**: EPS and FCF both calculate successfully
2. **EPS succeeds, FCF fails**: Due to insufficient data
3. **EPS fails, FCF succeeds**: Missing EPS but cash flow available
4. **Both fail**: Neither can be calculated
5. **Negative FCF**: Calculated but flagged
6. **Cache hits**: Both APIs use cached data
7. **Force refresh**: Both APIs fetch fresh data

### Mock Data Structure:

**OVERVIEW mock**:
```python
{
    "Symbol": "AAPL",
    "EPS": "6.42",
    "SharesOutstanding": "15000000000",
    "PERatio": "25.5"
}
```

**CASH_FLOW mock**:
```python
{
    "symbol": "AAPL",
    "quarterlyReports": [
        {
            "fiscalDateEnding": "2024-09-30",
            "operatingCashflow": "30000000000",
            "capitalExpenditures": "-2500000000"
        },
        # ... 3 more quarters
    ]
}
```

## Testing Checklist

### Unit Test Verification:
- [ ] All FCF edge case tests pass
- [ ] Mathematical accuracy verified
- [ ] Error conditions raise appropriate exceptions
- [ ] Decimal precision maintained

### Integration Test Verification:
- [ ] Dual calculation works end-to-end
- [ ] Independent failure handling works
- [ ] Cache behavior correct for both APIs
- [ ] Summary output format correct
- [ ] Database updates verified

### Coverage Verification:
- [ ] Run coverage report: `just test --cov=scanner.valuation --cov=scanner.management.commands.calculate_intrinsic_value --cov-report=html`
- [ ] Check FCF functions >95% coverage
- [ ] Check command >90% coverage
- [ ] Review uncovered lines and add tests if critical

### Performance Verification:
- [ ] Tests run quickly (mocked APIs)
- [ ] No actual API calls made in tests
- [ ] Database isolation works (tests don't interfere)

## Reference

**Testing Documentation:**
- pytest: https://docs.pytest.org/
- pytest-django: https://pytest-django.readthedocs.io/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html

**Coverage:**
- pytest-cov: https://pytest-cov.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/
