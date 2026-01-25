# Contributing to pytest-testrail

Thank you for your interest in contributing to pytest-testrail! This document provides guidelines and instructions for contributing.

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Getting Started

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/pytest-testrail.git
   cd pytest-testrail
   ```

2. **Install dependencies**

   ```bash
   uv sync
   ```

   This creates a virtual environment and installs all dependencies including dev tools.

3. **Verify installation**

   ```bash
   uv run pytest
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=pytest_testrail --cov-report=term-missing

# Run specific test
uv run pytest tests/test_plugin.py::test_name -v
```

### Code Quality

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [mypy](https://mypy.readthedocs.io/) for type checking.

```bash
# Run linter
uv run ruff check pytest_testrail tests

# Auto-fix linting issues
uv run ruff check --fix pytest_testrail tests

# Format code
uv run ruff format pytest_testrail tests

# Run type checker
uv run mypy pytest_testrail
```

### Testing Multiple Python Versions

Use uv to test across Python versions:

```bash
# Test with specific Python version
uv run --python 3.10 pytest
uv run --python 3.11 pytest
uv run --python 3.12 pytest
uv run --python 3.13 pytest

# Or use a script to test all versions
for v in 3.10 3.11 3.12 3.13; do uv run --python $v pytest; done
```

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates

### Commit Messages

Write clear, concise commit messages:

```
Add pagination support for get_tests API

- Handle TestRail 6.7+ paginated responses
- Add get_paginated() method to APIClient
- Update plugin to use pagination for large test suites
```

### Code Style

- Use type hints for all function signatures
- Follow existing code patterns
- Keep functions focused and small
- Add docstrings for public APIs

### Adding Tests

All new features and bug fixes should include tests:

```python
def test_new_feature(mocker):
    """Test description of what's being tested."""
    # Arrange
    mock_api = mocker.Mock()
    
    # Act
    result = function_under_test(mock_api)
    
    # Assert
    assert result == expected_value
```

## Pull Request Process

1. **Create a feature branch**

   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**
   - Write code
   - Add/update tests
   - Update documentation if needed

3. **Run quality checks**

   ```bash
   uv run ruff check pytest_testrail tests
   uv run mypy pytest_testrail
   uv run pytest
   ```

4. **Commit and push**

   ```bash
   git add .
   git commit -m "Add my feature"
   git push origin feature/my-feature
   ```

5. **Open a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI checks pass

## Reporting Issues

When reporting issues, please include:

- Python version (`python --version`)
- pytest-testrail version (`pip show pytest-testrail`)
- TestRail version (if known)
- Minimal code example to reproduce
- Full error traceback

## Feature Requests

Feature requests are welcome! Please:

- Check existing issues first
- Describe the use case
- Explain how it benefits users

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for any questions about contributing.
