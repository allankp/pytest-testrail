# -*- coding: UTF-8 -*-
"""
pytest-testrail - A pytest plugin for TestRail integration.

This plugin allows you to automatically create test runs and publish
test results to TestRail.

Example:
    >>> from pytest_testrail.plugin import pytestrail
    >>>
    >>> @pytestrail.case('C1234', 'C5678')
    ... def test_example():
    ...     assert True

For more information, see https://github.com/allankp/pytest-testrail
"""
from pytest_testrail.plugin import pytestrail, testrail
from pytest_testrail.testrail_api import (
    APIClient,
    TestRailAPIError,
    TestRailAuthenticationError,
    TestRailError,
    TestRailRateLimitError,
)

__version__ = "3.0.0"
__all__ = [
    "pytestrail",
    "testrail",
    "APIClient",
    "TestRailError",
    "TestRailAPIError",
    "TestRailAuthenticationError",
    "TestRailRateLimitError",
]
