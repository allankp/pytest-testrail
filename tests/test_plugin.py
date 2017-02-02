from datetime import datetime
from freezegun import freeze_time
from mock import create_autospec, Mock
import pytest

from pytest_testrail import plugin
from pytest_testrail.plugin import TestRailPlugin
from pytest_testrail.testrail_api import APIClient

pytest_plugins = "pytester"

ASSIGN_USER_ID = 3
FAKE_NOW = datetime(2015, 1, 31, 19, 5, 42)
PROJECT_ID = 4
PYTEST_FILE = """
    from pytest_testrail.plugin import testrail
    @testrail('C1234', 'C5678')
    def test_func():
        pass
"""

PYTEST_SUITE_FILE = """
    from pytest_testrail.plugin import suite_testrail
    @suite_testrail('S12', 'C1234', 'C5678')
    def test_func():
        pass
"""
SUITE_ID = 1
TR_NAME = None


@pytest.fixture
def api_client():
    return create_autospec(APIClient)


@pytest.fixture
def tr_plugin(api_client):
    """
    Creates a TestRailPlugin that is set for test run creation
    :param api_client:
    :return:
    """
    return TestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, True, TR_NAME)


@pytest.fixture
def tp_plugin(api_client):
    """
    Creates a TestRailPlugin that is set for test plan creation
    :param api_client:
    :return:
    """
    return TestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, True, TR_NAME, True)


@pytest.fixture
def pytest_test_items(testdir):
    testdir.makepyfile(PYTEST_FILE)
    return [testdir.getitem(PYTEST_FILE)]


@pytest.fixture
def pytest_test_suite_items(testdir):
    testdir.makepyfile(PYTEST_SUITE_FILE)
    return [testdir.getitem(PYTEST_SUITE_FILE)]


@freeze_time(FAKE_NOW)
def test_testrun_name():
    assert plugin.testrun_name() == 'Automated Run {}'.format(FAKE_NOW.strftime(plugin.DT_FORMAT))


def test_failed_outcome(tr_plugin):
    assert plugin.get_test_outcome('failed') == plugin.PYTEST_TO_TESTRAIL_STATUS['failed']


def test_successful_outcome(tr_plugin):
    passed_outcome = plugin.PYTEST_TO_TESTRAIL_STATUS['passed']
    assert plugin.get_test_outcome('passed') == passed_outcome


def test_clean_test_ids():
    assert list(plugin.clean_test_ids(['C1234', 'C12345'])) == [1234, 12345]


def test_clean_suite_ids():
    assert plugin.clean_suite_ids('S1234') == 1234


def test_get_testrail_keys(pytest_test_items, testdir):
    assert plugin.get_testrail_keys(pytest_test_items) == [1234, 5678]


def test_get_testrail_suite_keys(pytest_test_suite_items, testdir):
    expected = {12: [1234, 5678]}
    assert plugin.get_testrail_suite_and_keys(pytest_test_suite_items) == expected


def test_add_result(tr_plugin):
    tr_plugin.add_result([1, 2], 3)

    expected_results = [
        {
            'case_id': 1,
            'status_id': 3,
        },
        {
            'case_id': 2,
            'status_id': 3,
        }
    ]

    assert tr_plugin.results == expected_results


def test_add_suite_result(tp_plugin):
    tp_plugin.add_suite_result(1, [1, 2], 3)
    tp_plugin.add_suite_result(1, [3], 3)
    tp_plugin.add_suite_result(2, [4], 3)

    expected_results = {
        1: [
            {
                'case_id': 1,
                'status_id': 3,
            },
            {
                'case_id': 2,
                'status_id': 3,
            },
            {
                'case_id': 3,
                'status_id': 3,
            }
        ],
        2: [
            {
                'case_id': 4,
                'status_id': 3,
            }
        ]
    }

    assert tp_plugin.results == expected_results


def pytest_runtest_makereport(pytest_test_items, tr_plugin):
    keys = ['C4354', 'C1234']
    report = Mock(keywords={key: None for key in keys}, failed=True, when='teardown')

    tr_plugin.pytest_runtest_makereport(report)

    expected_results = [
        {
            'case_id': '4354',
            'status_id': 1,
        },
        {
            'case_id': '1234',
            'status_id': 1,
        }
    ]

    assert tr_plugin.results == expected_results


def test_pytest_sessionfinish(api_client, tr_plugin):
    tr_plugin.results = [1, 2]
    tr_plugin.testrun_id = 10

    tr_plugin.pytest_sessionfinish(None, 0)

    expected_uri = plugin.ADD_RESULTS_URL.format(10)
    expected_data = {'results': [1, 2]}
    check_cert = True
    api_client.send_post.assert_called_once_with(expected_uri, expected_data, check_cert)


def test_create_test_run(api_client, tr_plugin):
    expected_tr_keys = [3453, 234234, 12]
    expect_name = 'testrun_name'

    tr_plugin.create_test_run(ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, expect_name, expected_tr_keys)

    expected_uri = plugin.ADD_TESTRUN_URL.format(PROJECT_ID)
    expected_data = {
        'suite_id': SUITE_ID,
        'name': expect_name,
        'assignedto_id': ASSIGN_USER_ID,
        'include_all': False,
        'case_ids': expected_tr_keys
    }
    check_cert = True
    api_client.send_post.assert_called_once_with(expected_uri, expected_data, check_cert)


def test_create_test_plan(api_client, tp_plugin):
    expected_suite_and_keys = {1: [3453, 234234, 12],
                               2: [123, 8, 10]}
    expect_name = 'testrun_name'

    tp_plugin.create_test_plan(ASSIGN_USER_ID, PROJECT_ID, expect_name, expected_suite_and_keys)
    expected_uri = plugin.ADD_TESTPLAN_URL.format(PROJECT_ID)
    expected_data = {
        'name': 'testrun_name',
        'entries': [
            {'assignedto_id': 3,
             'include_all': False,
             'suite_id': 1,
             'case_ids': [3453, 234234, 12]},
            {'assignedto_id': 3,
             'include_all': False,
             'suite_id': 2,
             'case_ids': [123, 8, 10]}
        ]
    }
    check_cert = True
    api_client.send_post.assert_called_once_with(expected_uri, expected_data, check_cert)
