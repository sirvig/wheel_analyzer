# Ad-hoc tasks

Pending:

Completed:
- Fix failing tests. When running `just test` there were 11 failing tests (not 20). Fixed all test failures related to:
  - URL namespace issues (scanner app uses `app_name = "scanner"`)
  - Template include path issues (tracker partials)
  - Authentication issues (missing `user` fixture and `force_login` calls)
  - Mock configuration issues (Redis mock setup)
  - Test assertion issues (expectations didn't match async view behavior)
  - Result: All 180 tests now passing ✅
