# -*- coding: UTF-8 -*-
"""
pytest-testrail plugin.

This module provides pytest integration with TestRail for automatic
test result reporting.
"""
from __future__ import annotations

import logging
import re
import warnings
from datetime import datetime, timezone
from operator import itemgetter
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config

    from .testrail_api import APIClient

logger = logging.getLogger(__name__)

# Reference: https://support.testrail.com/hc/en-us/articles/7077935129364-Statuses
TESTRAIL_TEST_STATUS = {
    "passed": 1,
    "blocked": 2,
    "untested": 3,
    "retest": 4,
    "failed": 5,
}

PYTEST_TO_TESTRAIL_STATUS = {
    "passed": TESTRAIL_TEST_STATUS["passed"],
    "failed": TESTRAIL_TEST_STATUS["failed"],
    "skipped": TESTRAIL_TEST_STATUS["blocked"],
}

DT_FORMAT = "%d-%m-%Y %H:%M:%S"

TESTRAIL_PREFIX = "testrail"
TESTRAIL_DEFECTS_PREFIX = "testrail_defects"
ADD_RESULTS_URL = "add_results_for_cases/{}"
ADD_TESTRUN_URL = "add_run/{}"
CLOSE_TESTRUN_URL = "close_run/{}"
CLOSE_TESTPLAN_URL = "close_plan/{}"
GET_TESTRUN_URL = "get_run/{}"
GET_TESTPLAN_URL = "get_plan/{}"
GET_TESTS_URL = "get_tests/{}"

COMMENT_SIZE_LIMIT = 4000


class DeprecatedTestDecorator(DeprecationWarning):
    """Warning for deprecated test decorators."""

    pass


warnings.simplefilter(action="once", category=DeprecatedTestDecorator, lineno=0)


class pytestrail:
    """
    Alternative to using the testrail function as a decorator.

    Using this class avoids pytest confusing it as a test function
    since it has the 'test' prefix.

    Example:
        >>> @pytestrail.case('C123', 'C456')
        ... def test_something():
        ...     pass
        ...
        >>> @pytestrail.defect('BUG-123')
        ... def test_bugfix():
        ...     pass
    """

    @staticmethod
    def case(*ids: str) -> pytest.MarkDecorator:
        """
        Decorator to mark tests with TestRail case IDs.

        Args:
            *ids: TestRail case IDs (e.g., 'C123', 'C456').

        Returns:
            A pytest marker.

        Example:
            >>> @pytestrail.case('C123', 'C456')
            ... def test_feature():
            ...     pass
        """
        return pytest.mark.testrail(ids=ids)

    @staticmethod
    def defect(*defect_ids: str) -> pytest.MarkDecorator:
        """
        Decorator to mark tests with defect IDs.

        Args:
            *defect_ids: Defect/issue IDs (e.g., 'BUG-123', 'JIRA-456').

        Returns:
            A pytest marker.

        Example:
            >>> @pytestrail.defect('BUG-123', 'JIRA-456')
            ... def test_bugfix():
            ...     pass
        """
        return pytest.mark.testrail_defects(defect_ids=defect_ids)


def testrail(*ids: str) -> pytest.MarkDecorator:
    """
    Decorator to mark tests with TestRail case IDs.

    .. deprecated::
        Use :func:`pytestrail.case` instead.

    Args:
        *ids: TestRail case IDs (e.g., 'C123', 'C456').

    Returns:
        A pytest marker.
    """
    deprecation_msg = (
        "pytest_testrail: the @testrail decorator is deprecated and will be removed. "
        "Please use the @pytestrail.case decorator instead."
    )
    warnings.warn(deprecation_msg, DeprecatedTestDecorator, stacklevel=2)
    return pytestrail.case(*ids)


def get_test_outcome(outcome: str) -> int:
    """
    Return numerical value of test outcome.

    Args:
        outcome: pytest reported test outcome value.

    Returns:
        TestRail status ID.
    """
    return PYTEST_TO_TESTRAIL_STATUS[outcome]


def testrun_name() -> str:
    """Generate a default testrun name with timestamp."""
    now = datetime.now(timezone.utc)
    return f"Automated Run {now.strftime(DT_FORMAT)}"


def clean_test_ids(test_ids: tuple[str, ...]) -> list[int]:
    """
    Extract numeric test IDs from TestRail case markers.

    Args:
        test_ids: List of test IDs (e.g., ['C1234', 'C5678']).

    Returns:
        List of numeric test IDs.
    """
    result = []
    for test_id in test_ids:
        match = re.search(r"(?P<test_id>[0-9]+$)", test_id)
        if match:
            result.append(int(match.group("test_id")))
    return result


def clean_test_defects(defect_ids: tuple[str, ...]) -> list[str]:
    """
    Clean pytest marker containing TestRail defect IDs.

    Args:
        defect_ids: List of defect IDs.

    Returns:
        List of cleaned defect IDs.
    """
    return list(defect_ids)


def get_testrail_keys(items: list[Any]) -> list[tuple[Any, list[int]]]:
    """
    Extract TestRail case IDs from pytest items.

    Args:
        items: List of pytest test items.

    Returns:
        List of tuples containing (item, [case_ids]).
    """
    testcaseids = []
    for item in items:
        marker = item.get_closest_marker(TESTRAIL_PREFIX)
        if marker:
            ids = marker.kwargs.get("ids", ())
            testcaseids.append((item, clean_test_ids(ids)))
    return testcaseids


class PyTestRailPlugin:
    """
    pytest plugin for TestRail integration.

    This plugin handles test collection, result reporting, and testrun
    management with TestRail.
    """

    def __init__(
        self,
        client: APIClient,
        assign_user_id: int | str | None,
        project_id: int | str,
        suite_id: int | str,
        include_all: bool,
        cert_check: bool,
        tr_name: str | None,
        tr_description: str = "",
        run_id: int | str = 0,
        plan_id: int | str = 0,
        version: str = "",
        close_on_complete: bool = False,
        publish_blocked: bool = True,
        skip_missing: bool = False,
        milestone_id: int | str | None = None,
        custom_comment: str | None = None,
    ) -> None:
        """
        Initialize the TestRail plugin.

        Args:
            client: The TestRail API client.
            assign_user_id: User ID to assign the test run to.
            project_id: TestRail project ID.
            suite_id: TestRail suite ID.
            include_all: Include all test cases from suite.
            cert_check: Whether to verify SSL certificates.
            tr_name: Name for the test run.
            tr_description: Description for the test run.
            run_id: Existing test run ID to use.
            plan_id: Existing test plan ID to use.
            version: Version string for test results.
            close_on_complete: Close the test run/plan on completion.
            publish_blocked: Publish results for blocked tests.
            skip_missing: Skip tests not present in the test run.
            milestone_id: Milestone ID to associate with the test run.
            custom_comment: Custom comment to add to test results.
        """
        self.assign_user_id = assign_user_id
        self.cert_check = cert_check
        self.client = client
        self.project_id = project_id
        self.results: list[dict[str, Any]] = []
        self.suite_id = suite_id
        self.include_all = include_all
        self.testrun_name = tr_name
        self.testrun_description = tr_description
        self.testrun_id = int(run_id) if run_id else 0
        self.testplan_id = int(plan_id) if plan_id else 0
        self.version = version
        self.close_on_complete = close_on_complete
        self.publish_blocked = publish_blocked
        self.skip_missing = skip_missing
        self.milestone_id = milestone_id
        self.custom_comment = custom_comment

    # pytest hooks

    def pytest_report_header(self, config: Config, start_path: Any) -> str:
        """Add extra-info in header."""
        message = "pytest-testrail: "
        if self.testplan_id:
            message += f"existing testplan #{self.testplan_id} selected"
        elif self.testrun_id:
            message += f"existing testrun #{self.testrun_id} selected"
        else:
            message += "a new testrun will be created"
        return message

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(
        self, session: Any, config: Config, items: list[Any]
    ) -> None:
        """Modify test collection based on TestRail test run contents."""
        items_with_tr_keys = get_testrail_keys(items)
        tr_keys = [case_id for item in items_with_tr_keys for case_id in item[1]]

        if self.testplan_id and self.is_testplan_available():
            self.testrun_id = 0
        elif self.testrun_id and self.is_testrun_available():
            self.testplan_id = 0
            if self.skip_missing:
                tests_list = [test.get("case_id") for test in self.get_tests(self.testrun_id)]
                for item, case_id in items_with_tr_keys:
                    if not set(case_id).intersection(set(tests_list)):
                        mark = pytest.mark.skip("Test is not present in testrun.")
                        item.add_marker(mark)
        else:
            if self.testrun_name is None:
                self.testrun_name = testrun_name()

            self.create_test_run(
                self.assign_user_id,
                self.project_id,
                self.suite_id,
                self.include_all,
                self.testrun_name,
                tr_keys,
                self.milestone_id,
                self.testrun_description,
            )

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item: Any, call: Any) -> Any:
        """Collect result and associated testcases (TestRail) of an execution."""
        outcome = yield
        rep = outcome.get_result()
        defectids = None

        test_parametrize = None
        if hasattr(item, "callspec"):
            test_parametrize = item.callspec.params

        comment = rep.longrepr
        if item.get_closest_marker(TESTRAIL_DEFECTS_PREFIX):
            defectids = item.get_closest_marker(TESTRAIL_DEFECTS_PREFIX).kwargs.get("defect_ids")

        if item.get_closest_marker(TESTRAIL_PREFIX):
            testcaseids = item.get_closest_marker(TESTRAIL_PREFIX).kwargs.get("ids")
            if rep.when == "call" and testcaseids:
                defects_str = None
                if defectids:
                    defects_str = ", ".join(clean_test_defects(defectids))

                self.add_result(
                    clean_test_ids(testcaseids),
                    get_test_outcome(outcome.get_result().outcome),
                    comment=comment,
                    duration=rep.duration,
                    defects=defects_str,
                    test_parametrize=test_parametrize,
                )

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        """Publish results in TestRail."""
        logger.info("Start publishing results to TestRail")
        if self.results:
            tests_list = [str(result["case_id"]) for result in self.results]
            logger.info("Testcases to publish: %s", ", ".join(tests_list))

            if self.testrun_id:
                self.add_results(self.testrun_id)
            elif self.testplan_id:
                testruns = self.get_available_testruns(self.testplan_id)
                logger.info("Testruns to update: %s", ", ".join(str(elt) for elt in testruns))
                for testrun_id in testruns:
                    self.add_results(testrun_id)
            else:
                logger.warning("No test run or test plan configured, results not published")

            if self.close_on_complete and self.testrun_id:
                self.close_test_run(self.testrun_id)
            elif self.close_on_complete and self.testplan_id:
                self.close_test_plan(self.testplan_id)
        logger.info("Finished publishing results to TestRail")

    # Plugin methods

    def add_result(
        self,
        test_ids: list[int],
        status: int,
        comment: Any = "",
        defects: str | None = None,
        duration: float = 0,
        test_parametrize: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a new result to be submitted at the end.

        Args:
            test_ids: List of TestRail case IDs.
            status: TestRail status code.
            comment: Test failure/error message.
            defects: Comma-separated list of defect IDs.
            duration: Test execution time in seconds.
            test_parametrize: Pytest parametrize values.
        """
        for test_id in test_ids:
            data = {
                "case_id": test_id,
                "status_id": status,
                "comment": comment,
                "duration": duration,
                "defects": defects,
                "test_parametrize": test_parametrize,
            }
            self.results.append(data)

    def add_results(self, testrun_id: int) -> None:
        """
        Submit all collected results to TestRail.

        Args:
            testrun_id: The TestRail test run ID.
        """
        # Sort results by case_id
        self.results.sort(key=itemgetter("case_id"))

        # Manage case of "blocked" testcases
        if self.publish_blocked is False:
            logger.info("Option 'Don't publish blocked testcases' activated")
            blocked_tests_list = [
                test.get("case_id")
                for test in self.get_tests(testrun_id)
                if test.get("status_id") == TESTRAIL_TEST_STATUS["blocked"]
            ]
            logger.info("Blocked testcases excluded: %s", ", ".join(str(elt) for elt in blocked_tests_list))
            self.results = [result for result in self.results if result.get("case_id") not in blocked_tests_list]

        # Log if include_all is enabled
        if self.include_all:
            logger.info("Option 'Include all testcases from test suite for test run' activated")

        # Build results payload
        data: dict[str, list[dict[str, Any]]] = {"results": []}
        for result in self.results:
            entry: dict[str, Any] = {
                "status_id": result["status_id"],
                "case_id": result["case_id"],
                "defects": result["defects"],
            }
            if self.version:
                entry["version"] = self.version

            comment = result.get("comment", "")
            test_parametrize = result.get("test_parametrize", "")
            entry["comment"] = ""

            if test_parametrize:
                entry["comment"] += "# Test parametrize: #\n"
                entry["comment"] += str(test_parametrize) + "\n\n"

            if comment:
                if self.custom_comment:
                    entry["comment"] += self.custom_comment + "\n"
                # Indent text to avoid string formatting by TestRail. Limit size of comment.
                entry["comment"] += "# Pytest result: #\n"
                comment_str = str(comment)
                if len(comment_str) > COMMENT_SIZE_LIMIT:
                    entry["comment"] += "Log truncated\n...\n"
                entry["comment"] += "    " + comment_str[-COMMENT_SIZE_LIMIT:].replace("\n", "\n    ")
            elif comment == "":
                entry["comment"] = self.custom_comment or ""

            duration = result.get("duration")
            if duration:
                # TestRail API doesn't manage milliseconds
                duration_int = 1 if duration < 1 else int(round(duration))
                entry["elapsed"] = f"{duration_int}s"

            data["results"].append(entry)

        try:
            self.client.send_post(
                ADD_RESULTS_URL.format(testrun_id),
                data,
                cert_check=self.cert_check,
            )
            logger.info("Successfully published %d results", len(data["results"]))
        except Exception as e:
            logger.error("Failed to publish results: %s", e)

    def create_test_run(
        self,
        assign_user_id: int | str | None,
        project_id: int | str,
        suite_id: int | str,
        include_all: bool,
        testrun_name: str,
        tr_keys: list[int],
        milestone_id: int | str | None,
        description: str = "",
    ) -> None:
        """
        Create a new test run in TestRail.

        Args:
            assign_user_id: User to assign the test run to.
            project_id: TestRail project ID.
            suite_id: TestRail suite ID.
            include_all: Include all test cases from suite.
            testrun_name: Name for the test run.
            tr_keys: List of test case IDs to include.
            milestone_id: Milestone to associate with.
            description: Description for the test run.
        """
        data: dict[str, Any] = {
            "suite_id": suite_id,
            "name": testrun_name,
            "description": description,
            "assignedto_id": assign_user_id,
            "include_all": include_all,
            "case_ids": tr_keys,
            "milestone_id": milestone_id,
        }

        try:
            response = self.client.send_post(
                ADD_TESTRUN_URL.format(project_id),
                data,
                cert_check=self.cert_check,
            )
            if isinstance(response, dict):
                self.testrun_id = response["id"]
                logger.info('New testrun created with name "%s" and ID=%s', testrun_name, self.testrun_id)
        except Exception as e:
            logger.error("Failed to create testrun: %s", e)

    def close_test_run(self, testrun_id: int) -> None:
        """Close a test run in TestRail."""
        try:
            self.client.send_post(
                CLOSE_TESTRUN_URL.format(testrun_id),
                data={},
                cert_check=self.cert_check,
            )
            logger.info("Test run with ID=%s was closed", testrun_id)
        except Exception as e:
            logger.error("Failed to close test run: %s", e)

    def close_test_plan(self, testplan_id: int) -> None:
        """Close a test plan in TestRail."""
        try:
            self.client.send_post(
                CLOSE_TESTPLAN_URL.format(testplan_id),
                data={},
                cert_check=self.cert_check,
            )
            logger.info("Test plan with ID=%s was closed", testplan_id)
        except Exception as e:
            logger.error("Failed to close test plan: %s", e)

    def is_testrun_available(self) -> bool:
        """
        Check if the test run is available in TestRail.

        Returns:
            True if testrun exists AND is open.
        """
        try:
            response = self.client.send_get(
                GET_TESTRUN_URL.format(self.testrun_id),
                cert_check=self.cert_check,
            )
            if isinstance(response, dict):
                return response.get("is_completed") is False
        except Exception as e:
            logger.error("Failed to retrieve testrun: %s", e)
        return False

    def is_testplan_available(self) -> bool:
        """
        Check if the test plan is available in TestRail.

        Returns:
            True if testplan exists AND is open.
        """
        try:
            response = self.client.send_get(
                GET_TESTPLAN_URL.format(self.testplan_id),
                cert_check=self.cert_check,
            )
            if isinstance(response, dict):
                return response.get("is_completed") is False
        except Exception as e:
            logger.error("Failed to retrieve testplan: %s", e)
        return False

    def get_available_testruns(self, plan_id: int) -> list[int]:
        """
        Get available test runs from a test plan.

        Args:
            plan_id: TestRail test plan ID.

        Returns:
            List of available test run IDs.
        """
        testruns_list: list[int] = []
        try:
            response = self.client.send_get(
                GET_TESTPLAN_URL.format(plan_id),
                cert_check=self.cert_check,
            )
            if isinstance(response, dict):
                for entry in response.get("entries", []):
                    for run in entry.get("runs", []):
                        if not run.get("is_completed"):
                            testruns_list.append(run["id"])
        except Exception as e:
            logger.error("Failed to retrieve testplan: %s", e)
        return testruns_list

    def get_tests(self, run_id: int) -> list[dict[str, Any]]:
        """
        Get tests from a test run (with pagination support).

        Args:
            run_id: TestRail test run ID.

        Returns:
            List of tests in the test run.
        """
        try:
            response = self.client.send_get(
                GET_TESTS_URL.format(run_id),
                cert_check=self.cert_check,
            )
            # Handle paginated response (TestRail 6.7+)
            if isinstance(response, dict) and "tests" in response:
                # Use pagination for large test runs
                return list(self.client.get_paginated(
                    GET_TESTS_URL.format(run_id),
                    "tests",
                    cert_check=self.cert_check,
                ))
            # Handle legacy non-paginated response
            elif isinstance(response, list):
                return response
        except Exception as e:
            logger.error("Failed to get tests: %s", e)
        return []
