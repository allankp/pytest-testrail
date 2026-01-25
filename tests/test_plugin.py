# -*- coding: UTF-8 -*-
"""Tests for pytest-testrail plugin."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, create_autospec

import pytest
from freezegun import freeze_time

from pytest_testrail import plugin
from pytest_testrail.plugin import TESTRAIL_TEST_STATUS, PyTestRailPlugin
from pytest_testrail.testrail_api import APIClient

pytest_plugins = "pytester"

ASSIGN_USER_ID = 3
FAKE_NOW = datetime(2015, 1, 31, 19, 5, 42)
MILESTONE_ID = 5
PROJECT_ID = 4
PYTEST_FILE = """
    from pytest_testrail.plugin import testrail, pytestrail
    @testrail('C1234', 'C5678')
    def test_func():
        pass
    @pytestrail.case('C8765', 'C4321')
    @pytestrail.defect('PF-418', 'PF-517')
    def test_other_func():
        pass
"""
SUITE_ID = 1
TR_NAME = None
DESCRIPTION = "This is a test description"
TESTPLAN = {
    "id": 58,
    "is_completed": False,
    "entries": [
        {
            "id": "ce2f3c8f-9899-47b9-a6da-db59a66fb794",
            "name": "Test Run 5/23/2017",
            "runs": [
                {
                    "id": 59,
                    "name": "Test Run 5/23/2017",
                    "is_completed": False,
                }
            ],
        },
        {
            "id": "084f680c-f87a-402e-92be-d9cc2359b9a7",
            "name": "Test Run 5/23/2017",
            "runs": [
                {
                    "id": 60,
                    "name": "Test Run 5/23/2017",
                    "is_completed": True,
                }
            ],
        },
        {
            "id": "775740ff-1ba3-4313-a9df-3acd9d5ef967",
            "name": "Test Run 5/23/2017",
            "runs": [
                {
                    "id": 61,
                    "is_completed": False,
                }
            ],
        },
    ],
}

CUSTOM_COMMENT = "This is custom comment"


@pytest.fixture
def api_client() -> MagicMock:
    """Create a mock API client."""
    spec = create_autospec(APIClient)
    spec.get_error = APIClient.get_error  # don't mock get_error
    return spec


@pytest.fixture
def tr_plugin(api_client: MagicMock) -> PyTestRailPlugin:
    """Create a TestRail plugin instance for testing."""
    return PyTestRailPlugin(
        api_client,
        ASSIGN_USER_ID,
        PROJECT_ID,
        SUITE_ID,
        False,
        True,
        TR_NAME,
        DESCRIPTION,
        version="1.0.0.0",
        milestone_id=MILESTONE_ID,
        custom_comment=CUSTOM_COMMENT,
    )


@pytest.fixture
def pytest_test_items(testdir: Any) -> list[Any]:
    """Create pytest test items from test file."""
    testdir.makepyfile(PYTEST_FILE)
    return [item for item in testdir.getitems(PYTEST_FILE) if item.name != "testrail"]


@freeze_time(FAKE_NOW)
def test_testrun_name() -> None:
    """Test testrun name generation."""
    assert plugin.testrun_name() == f"Automated Run {FAKE_NOW.strftime(plugin.DT_FORMAT)}"


def test_failed_outcome(tr_plugin: PyTestRailPlugin) -> None:
    """Test failed outcome mapping."""
    assert plugin.get_test_outcome("failed") == plugin.PYTEST_TO_TESTRAIL_STATUS["failed"]


def test_successful_outcome(tr_plugin: PyTestRailPlugin) -> None:
    """Test successful outcome mapping."""
    passed_outcome = plugin.PYTEST_TO_TESTRAIL_STATUS["passed"]
    assert plugin.get_test_outcome("passed") == passed_outcome


def test_clean_test_ids() -> None:
    """Test test ID cleaning."""
    assert list(plugin.clean_test_ids(("C1234", "C12345"))) == [1234, 12345]


def test_clean_test_defects() -> None:
    """Test defect ID cleaning."""
    assert list(plugin.clean_test_defects(("PF-123", "BUG-456"))) == ["PF-123", "BUG-456"]


def test_get_testrail_keys(pytest_test_items: list[Any], testdir: Any) -> None:
    """Test extracting TestRail keys from test items."""
    items = plugin.get_testrail_keys(pytest_test_items)
    assert list(items[0][1]) == [1234, 5678]
    assert list(items[1][1]) == [8765, 4321]


def test_add_result(tr_plugin: PyTestRailPlugin) -> None:
    """Test adding a test result."""
    status = TESTRAIL_TEST_STATUS["passed"]
    tr_plugin.add_result([1, 2], status, comment="ERROR!", duration=3600, defects="PF-456")

    expected_results = [
        {
            "case_id": 1,
            "status_id": status,
            "comment": "ERROR!",
            "duration": 3600,
            "defects": "PF-456",
            "test_parametrize": None,
        },
        {
            "case_id": 2,
            "status_id": status,
            "comment": "ERROR!",
            "duration": 3600,
            "defects": "PF-456",
            "test_parametrize": None,
        },
    ]

    assert tr_plugin.results == expected_results


def test_pytest_runtest_makereport(
    pytest_test_items: list[Any], tr_plugin: PyTestRailPlugin, testdir: Any
) -> None:
    """Test collecting test results."""

    class Outcome:
        def __init__(self) -> None:
            testdir.makepyfile(PYTEST_FILE)
            self.result = testdir.runpytest()
            self.result.when = "call"
            self.result.longrepr = "An error"
            self.result.outcome = "failed"
            self.result.duration = 2

        def get_result(self) -> Any:
            return self.result

    outcome = Outcome()
    f = tr_plugin.pytest_runtest_makereport(pytest_test_items[0], None)
    f.send(None)
    try:
        f.send(outcome)
    except StopIteration:
        pass

    expected_results = [
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["failed"],
            "comment": "An error",
            "duration": 2,
            "defects": None,
            "test_parametrize": None,
        },
        {
            "case_id": 5678,
            "status_id": TESTRAIL_TEST_STATUS["failed"],
            "comment": "An error",
            "duration": 2,
            "defects": None,
            "test_parametrize": None,
        },
    ]
    assert tr_plugin.results == expected_results


def test_pytest_sessionfinish(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test publishing results at session end."""
    tr_plugin.results = [
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["failed"],
            "duration": 2.6,
            "defects": "PF-516",
        },
        {
            "case_id": 5678,
            "status_id": TESTRAIL_TEST_STATUS["blocked"],
            "comment": "An error",
            "duration": 0.1,
            "defects": None,
        },
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["passed"],
            "duration": 2.6,
            "defects": "PF-517, PF-113",
        },
    ]
    tr_plugin.testrun_id = 10

    tr_plugin.pytest_sessionfinish(None, 0)

    expected_data = {
        "results": [
            {
                "case_id": 1234,
                "status_id": TESTRAIL_TEST_STATUS["failed"],
                "defects": "PF-516",
                "version": "1.0.0.0",
                "elapsed": "3s",
                "comment": CUSTOM_COMMENT,
            },
            {
                "case_id": 1234,
                "status_id": TESTRAIL_TEST_STATUS["passed"],
                "defects": "PF-517, PF-113",
                "version": "1.0.0.0",
                "elapsed": "3s",
                "comment": CUSTOM_COMMENT,
            },
            {
                "case_id": 5678,
                "status_id": TESTRAIL_TEST_STATUS["blocked"],
                "defects": None,
                "version": "1.0.0.0",
                "elapsed": "1s",
                "comment": f"{CUSTOM_COMMENT}\n# Pytest result: #\n    An error",
            },
        ]
    }

    api_client.send_post.assert_any_call(
        plugin.ADD_RESULTS_URL.format(tr_plugin.testrun_id), expected_data, cert_check=True
    )


def test_pytest_sessionfinish_testplan(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test publishing results to a test plan."""
    tr_plugin.results = [
        {
            "case_id": 5678,
            "status_id": TESTRAIL_TEST_STATUS["blocked"],
            "comment": "An error",
            "duration": 0.1,
            "defects": None,
        },
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["passed"],
            "duration": 2.6,
            "defects": None,
        },
    ]
    tr_plugin.testplan_id = 100
    tr_plugin.testrun_id = 0

    api_client.send_get.return_value = TESTPLAN
    tr_plugin.pytest_sessionfinish(None, 0)

    # Verify send_post was called for both available test runs (59 and 61)
    assert api_client.send_post.call_count == 2


@pytest.mark.parametrize("include_all", [True, False])
def test_create_test_run(api_client: MagicMock, tr_plugin: PyTestRailPlugin, include_all: bool) -> None:
    """Test creating a test run."""
    expected_tr_keys = [3453, 234234, 12]
    expect_name = "testrun_name"

    api_client.send_post.return_value = {"id": 123}

    tr_plugin.create_test_run(
        ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, include_all, expect_name, expected_tr_keys, MILESTONE_ID, DESCRIPTION
    )

    expected_uri = plugin.ADD_TESTRUN_URL.format(PROJECT_ID)
    expected_data = {
        "suite_id": SUITE_ID,
        "name": expect_name,
        "description": DESCRIPTION,
        "assignedto_id": ASSIGN_USER_ID,
        "include_all": include_all,
        "case_ids": expected_tr_keys,
        "milestone_id": MILESTONE_ID,
    }
    api_client.send_post.assert_called_once_with(expected_uri, expected_data, cert_check=True)


def test_is_testrun_available(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test checking if a test run is available."""
    tr_plugin.testrun_id = 100

    api_client.send_get.return_value = {"is_completed": False}
    assert tr_plugin.is_testrun_available() is True

    api_client.send_get.side_effect = Exception("An error occurred")
    assert tr_plugin.is_testrun_available() is False

    api_client.send_get.side_effect = None
    api_client.send_get.return_value = {"is_completed": True}
    assert tr_plugin.is_testrun_available() is False


def test_is_testplan_available(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test checking if a test plan is available."""
    tr_plugin.testplan_id = 100

    api_client.send_get.return_value = {"is_completed": False}
    assert tr_plugin.is_testplan_available() is True

    api_client.send_get.side_effect = Exception("An error occurred")
    assert tr_plugin.is_testplan_available() is False

    api_client.send_get.side_effect = None
    api_client.send_get.return_value = {"is_completed": True}
    assert tr_plugin.is_testplan_available() is False


def test_get_available_testruns(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test getting available test runs from a plan."""
    testplan_id = 100
    api_client.send_get.return_value = TESTPLAN
    assert tr_plugin.get_available_testruns(testplan_id) == [59, 61]


def test_close_test_run(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test closing a test run."""
    tr_plugin.results = [
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["failed"],
            "duration": 2.6,
            "defects": None,
        },
        {
            "case_id": 5678,
            "status_id": TESTRAIL_TEST_STATUS["blocked"],
            "comment": "An error",
            "duration": 0.1,
            "defects": None,
        },
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["passed"],
            "duration": 2.6,
            "defects": None,
        },
    ]
    tr_plugin.testrun_id = 10
    tr_plugin.close_on_complete = True
    tr_plugin.pytest_sessionfinish(None, 0)

    # Check that close was called
    expected_uri = plugin.CLOSE_TESTRUN_URL.format(tr_plugin.testrun_id)
    calls = [str(call) for call in api_client.send_post.call_args_list]
    assert any(expected_uri in call for call in calls)


def test_close_test_plan(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test closing a test plan."""
    tr_plugin.results = [
        {
            "case_id": 5678,
            "status_id": TESTRAIL_TEST_STATUS["blocked"],
            "comment": "An error",
            "duration": 0.1,
            "defects": None,
        },
        {
            "case_id": 1234,
            "status_id": TESTRAIL_TEST_STATUS["passed"],
            "duration": 2.6,
            "defects": None,
        },
    ]
    tr_plugin.testplan_id = 100
    tr_plugin.testrun_id = 0
    tr_plugin.close_on_complete = True

    api_client.send_get.return_value = TESTPLAN
    tr_plugin.pytest_sessionfinish(None, 0)

    # Check that close was called
    expected_uri = plugin.CLOSE_TESTPLAN_URL.format(tr_plugin.testplan_id)
    calls = [str(call) for call in api_client.send_post.call_args_list]
    assert any(expected_uri in call for call in calls)


def test_dont_publish_blocked(api_client: MagicMock) -> None:
    """Test not publishing blocked test results."""
    my_plugin = PyTestRailPlugin(
        api_client,
        ASSIGN_USER_ID,
        PROJECT_ID,
        SUITE_ID,
        False,
        True,
        TR_NAME,
        version="1.0.0.0",
        publish_blocked=False,
    )

    my_plugin.results = [
        {"case_id": 1234, "status_id": TESTRAIL_TEST_STATUS["blocked"], "defects": None},
        {"case_id": 5678, "status_id": TESTRAIL_TEST_STATUS["passed"], "defects": None},
    ]
    my_plugin.testrun_id = 10

    # Return tests with paginated format
    api_client.send_get.return_value = {
        "tests": [
            {"case_id": 1234, "status_id": TESTRAIL_TEST_STATUS["blocked"], "defects": None},
            {"case_id": 5678, "status_id": TESTRAIL_TEST_STATUS["passed"], "defects": None},
        ]
    }
    api_client.get_paginated.return_value = iter(
        [
            {"case_id": 1234, "status_id": TESTRAIL_TEST_STATUS["blocked"], "defects": None},
            {"case_id": 5678, "status_id": TESTRAIL_TEST_STATUS["passed"], "defects": None},
        ]
    )

    my_plugin.pytest_sessionfinish(None, 0)

    # Verify send_post was called
    assert api_client.send_post.called


def test_skip_missing_only_one_test(api_client: MagicMock, pytest_test_items: list[Any]) -> None:
    """Test skipping tests not present in test run."""
    my_plugin = PyTestRailPlugin(
        api_client,
        ASSIGN_USER_ID,
        PROJECT_ID,
        SUITE_ID,
        False,
        True,
        TR_NAME,
        run_id=10,
        version="1.0.0.0",
        publish_blocked=False,
        skip_missing=True,
    )

    # Return tests list (legacy format)
    api_client.send_get.return_value = [{"case_id": 1234}, {"case_id": 5678}]
    my_plugin.is_testrun_available = lambda: True

    my_plugin.pytest_collection_modifyitems(None, None, pytest_test_items)

    assert not pytest_test_items[0].get_closest_marker("skip")
    assert pytest_test_items[1].get_closest_marker("skip")


def test_skip_missing_correlation_tests(api_client: MagicMock, pytest_test_items: list[Any]) -> None:
    """Test skipping tests with correlation to test run."""
    my_plugin = PyTestRailPlugin(
        api_client,
        ASSIGN_USER_ID,
        PROJECT_ID,
        SUITE_ID,
        False,
        True,
        TR_NAME,
        run_id=10,
        version="1.0.0.0",
        publish_blocked=False,
        skip_missing=True,
    )

    # Return tests list (legacy format)
    api_client.send_get.return_value = [{"case_id": 1234}, {"case_id": 8765}]
    my_plugin.is_testrun_available = lambda: True

    my_plugin.pytest_collection_modifyitems(None, None, pytest_test_items)

    assert not pytest_test_items[0].get_closest_marker("skip")
    assert not pytest_test_items[1].get_closest_marker("skip")


def test_get_tests_with_pagination(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test getting tests with paginated API response."""
    # Simulate paginated response (TestRail 6.7+)
    api_client.send_get.return_value = {
        "offset": 0,
        "limit": 250,
        "size": 2,
        "_links": {"next": None, "prev": None},
        "tests": [{"case_id": 1234}, {"case_id": 5678}],
    }
    api_client.get_paginated.return_value = iter([{"case_id": 1234}, {"case_id": 5678}])

    tests = tr_plugin.get_tests(10)
    assert len(tests) == 2


def test_get_tests_legacy_format(api_client: MagicMock, tr_plugin: PyTestRailPlugin) -> None:
    """Test getting tests with legacy non-paginated API response."""
    # Simulate legacy response (before TestRail 6.7)
    api_client.send_get.return_value = [{"case_id": 1234}, {"case_id": 5678}]

    tests = tr_plugin.get_tests(10)
    assert len(tests) == 2
    assert tests[0]["case_id"] == 1234
