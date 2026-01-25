# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-01-25

### Breaking Changes

- **Python 3.10+ required** - Dropped support for Python 2.7, 3.8, and 3.9
- Removed deprecated Python 2 compatibility code
- Changed from `setup.py` to `pyproject.toml` for modern packaging

### Added

- **API Key Authentication** - New `--tr-api-key` option for secure API key authentication (recommended over password)
- **Pagination Support** - Full support for TestRail API pagination (TestRail 6.7+)
- **Custom Exception Classes** - New exception hierarchy for better error handling:
  - `TestRailError` - Base exception
  - `TestRailAPIError` - API-related errors
  - `TestRailAuthenticationError` - Authentication failures
  - `TestRailRateLimitError` - Rate limiting (HTTP 429)
- **Connection Pooling** - Uses `requests.Session` for better performance
- **Automatic Retry** - Retries on rate limiting and network errors
- **Type Hints** - Full type annotations throughout the codebase
- **Logging** - Proper logging instead of print statements

### Changed

- Migrated from `setup.py` to `pyproject.toml` with hatchling build system
- Migrated from tox to uv for dependency management and testing
- Updated CI/CD to use GitHub Actions with uv
- Modernized test suite using `unittest.mock`
- Use timezone-aware `datetime.now(timezone.utc)` instead of deprecated `utcnow()`

### Removed

- Python 2.7, 3.8, 3.9 support
- `setup.py`, `setup.cfg`, `MANIFEST.ini`
- `requirements/` directory (dependencies now in `pyproject.toml`)
- `tox.ini` (replaced by uv)
- `Makefile`
