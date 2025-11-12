# Ad-hoc tasks

Pending:

## Phase 6.1 Documentation Issues (Critical)
- [ ] **Create analytics test suite** (6-8 hours) - **BLOCKER FOR PRODUCTION**
  - Create `scanner/tests/test_analytics.py` with 20+ unit tests
  - Create `scanner/tests/test_analytics_views.py` with 10+ view tests
  - Test all 6 analytics functions: `calculate_volatility()`, `calculate_cagr()`, `calculate_correlation()`, `calculate_sensitivity()`, `get_stock_analytics()`, `get_portfolio_analytics()`
  - Test edge cases: empty data, single data point, None values, zero division
  - Test chart data JSON serialization and validation
  - Target: 30-40 new tests (total: 277-287 tests)

- [ ] **Update CLAUDE.md with Phase 6.1 documentation** (2 hours)
  - Add Chart.js to "Technology Stack" section
  - Add analytics module to "Django Apps → scanner" section
  - Document all 6 analytics functions with usage examples
  - Document new views: `analytics_view()`, updated `stock_history_view()`, `valuation_comparison_view()`
  - Add "Analytics & Visualization" feature overview
  - Update "Current Status" to reference Phase 6.1 completion

- [ ] **Update spec file with implementation notes** (1 hour)
  - Mark Task 5 (sensitivity analysis UI) as "DEFERRED"
  - Update Task 6 status to show tests incomplete
  - Add "Implementation Results" section with actual completion status
  - Note production readiness blocked by missing tests

## Phase 6.1 Documentation Issues (Moderate)
- [ ] **Update README.md test count and roadmap** (30 min)
  - Update "Testing" section (line 244) with actual test count (247 currently, or 277+ after analytics tests)
  - Update "Roadmap" section to show Phase 6.1 as completed (currently shows as planned)
  - Verify "Analytics & Visualization" feature description matches implementation

- [ ] **Add Chart.js configuration comments to templates** (1 hour)
  - Add HTML comments to `analytics.html`, `stock_history.html`, `valuation_comparison.html`
  - Document dark mode color computation approach
  - Explain responsive settings and Chart.js version choice
  - Note `spanGaps: true` rationale

Completed:
- [x] Fix failing tests. When running `just test` there were 11 failing tests (not 20). Fixed all test failures related to:
  - URL namespace issues (scanner app uses `app_name = "scanner"`)
  - Template include path issues (tracker partials)
  - Authentication issues (missing `user` fixture and `force_login` calls)
  - Mock configuration issues (Redis mock setup)
  - Test assertion issues (expectations didn't match async view behavior)
  - Result: All 180 tests now passing ✅

- [x] **VULN-001**: Add SRI hashes to Chart.js CDN imports (1 hour) ✅
  - Added `integrity="sha384-9nhczxUqK87bcKHh20fSQcTGD4qq5GhayNYSYWqwBkINBhOfQLg/P5HG5lF1urn4"` to all Chart.js script tags
  - Added `crossorigin="anonymous"` attribute
  - Updated 3 templates: `analytics.html`, `stock_history.html`, `valuation_comparison.html`
  - Supply chain attack risk mitigated

- [x] **VULN-002**: Implement rate limiting on analytics endpoints (4 hours) ✅
  - Installed `django-ratelimit==4.1.0`
  - Added `@ratelimit(key='user', rate='10/m', method='GET')` to 3 views
  - Added conditional caching with `@conditionally_cache(60 * 5)` (disabled in tests)
  - Created `templates/429.html` for rate limit exceeded page
  - DoS vulnerability mitigated

- [x] **VULN-003**: Sanitize JSON chart data to prevent XSS (2 hours) ✅
  - Added `ensure_ascii=True` to all `json.dumps()` calls in views.py
  - Ensures Unicode characters are properly escaped
  - 3 locations updated (lines 439, 550, 771)
  - XSS via chart labels prevented

- [x] **VULN-004**: Configure Content Security Policy headers (3 hours) ✅
  - Installed `django-csp==4.0`
  - Added CSP middleware to MIDDLEWARE list
  - Configured CSP directives using new django-csp 4.0 dictionary format
  - Fixed configuration to use `CONTENT_SECURITY_POLICY` with `DIRECTIVES` key
  - Imported constants: `SELF`, `NONE` from `csp.constants`
  - Whitelisted CDNs for scripts: `cdn.jsdelivr.net` (Chart.js, Flowbite), `cdn.tailwindcss.com`
  - Whitelisted CDNs for styles: `cdn.jsdelivr.net` (DaisyUI, Flowbite), `cdn.tailwindcss.com`
  - Allow unsafe-inline temporarily for Tailwind and Chart.js initialization
  - Prevents unauthorized resource loading
  - Ready for CSP violation reporting in production

- [x] **VULN-005**: Fix N+1 query problem in `get_portfolio_analytics()` (3 hours) ✅
  - Refactored to use `prefetch_related("valuationhistory_set")`
  - Updated `get_stock_analytics()` to accept optional `prefetched_history` parameter
  - Ensured compatibility with both QuerySet and list types
  - Reduced database queries from 26+ to 2-3
  - Performance optimization complete

- [x] **VULN-006**: Replace verbose error messages with generic ones (2 hours) ✅
  - Replaced `str(e)` with "Calculation failed" in user-facing responses
  - Added `exc_info=True` to all error logging for detailed server-side logs
  - Updated 2 locations: analytics.py lines 326 and 496
  - Information disclosure prevented

- [x] **VULN-007**: Configure security headers (1 hour) ✅
  - Added HSTS configuration (environment-specific)
  - `SECURE_HSTS_SECONDS = 31536000` (1 year) in production
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`
  - `X_FRAME_OPTIONS = "DENY"`
  - `SECURE_BROWSER_XSS_FILTER = True`
  - `SECURE_REFERRER_POLICY = "same-origin"`
  - SSL redirect enabled in production only
  - Security headers properly configured
