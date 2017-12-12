# -*- coding: UTF-8 -*-
from datetime import datetime
from freezegun import freeze_time
from mock import create_autospec, Mock
import pytest

from pytest_testrail import plugin
from pytest_testrail.plugin import PyTestRailPlugin
from pytest_testrail.testrail_api import APIClient


pytest_plugins = "pytester"

ASSIGN_USER_ID = 3
FAKE_NOW = datetime(2015, 1, 31, 19, 5, 42)
PROJECT_ID = 4
PYTEST_FILE = """
    from pytest_testrail.plugin import testrail, pytestrail
    @testrail('C1234', 'C5678')
    def test_func():
        pass

    @pytestrail.case('C8765', 'C4321')
    def test_other_func():
        pass
"""
SUITE_ID = 1
TR_NAME = None
TESTPLAN = {
        "id": 58,
        "is_completed": False,
        "entries": [{
            "id": "ce2f3c8f-9899-47b9-a6da-db59a66fb794",
            "name": "Test Run 5/23/2017",
            "runs": [{
                "id": 59,
                "name": "Test Run 5/23/2017",
                "is_completed": False,
            }]
        }, {
            "id": "084f680c-f87a-402e-92be-d9cc2359b9a7",
            "name": "Test Run 5/23/2017",
            "runs": [{
                "id": 60,
                "name": "Test Run 5/23/2017",
                "is_completed": True,
            }]
        }, {
            "id": "775740ff-1ba3-4313-a9df-3acd9d5ef967",
            "name": "Test Run 5/23/2017",
            "runs": [{
                "id": 61,
                "is_completed": False,
            }]
        }]
    }

@pytest.fixture
def api_client():
    spec = create_autospec(APIClient)
    spec.get_error = APIClient.get_error  # don't mock get_error
    return spec


@pytest.fixture
def tr_plugin(api_client):
    return PyTestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, True, TR_NAME, version='1.0.0.0')


@pytest.fixture
def pytest_test_items(testdir):
    testdir.makepyfile(PYTEST_FILE)
    return [item for item in testdir.getitems(PYTEST_FILE) if item.name != 'testrail']


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


def test_get_testrail_keys(pytest_test_items, testdir):
    assert plugin.get_testrail_keys(pytest_test_items) == [1234, 5678, 8765, 4321]


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


def pytest_runtest_makereport(tr_plugin):
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
    tr_plugin.results = [
        {'case_id': 1234, 'status_id': 1},
        {'case_id': 5678, 'status_id': 2},
    ]
    tr_plugin.testrun_id = 10

    tr_plugin.pytest_sessionfinish(None, 0)

    expected_uri = plugin.ADD_RESULT_URL.format(10, 1234)
    expected_data = {'status_id': 1, 'version': '1.0.0.0'}
    api_client.send_post.assert_any_call(expected_uri, expected_data, cert_check=True)

    expected_uri = plugin.ADD_RESULT_URL.format(10, 5678)
    expected_data = {'status_id': 2, 'version': '1.0.0.0'}
    api_client.send_post.assert_any_call(expected_uri, expected_data, cert_check=True)


def test_pytest_sessionfinish_testplan(api_client, tr_plugin):
    tr_plugin.results = [
        {'case_id': 1234, 'status_id': 1},
        {'case_id': 5678, 'status_id': 2},
    ]
    tr_plugin.testplan_id = 100
    tr_plugin.testrun_id = 0

    api_client.send_get.return_value = TESTPLAN
    tr_plugin.pytest_sessionfinish(None, 0)
    check_cert = True
    api_client.send_post.assert_any_call(plugin.ADD_RESULT_URL.format(59, 1234),
                                         {'status_id': 1, 'version': '1.0.0.0'}, cert_check=check_cert)
    api_client.send_post.assert_any_call(plugin.ADD_RESULT_URL.format(59, 5678),
                                         {'status_id': 2, 'version': '1.0.0.0'}, cert_check=check_cert)
    api_client.send_post.assert_any_call(plugin.ADD_RESULT_URL.format(61, 1234),
                                         {'status_id': 1, 'version': '1.0.0.0'}, cert_check=check_cert)
    api_client.send_post.assert_any_call(plugin.ADD_RESULT_URL.format(61, 5678),
                                         {'status_id': 2, 'version': '1.0.0.0'}, cert_check=check_cert)


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
    api_client.send_post.assert_called_once_with(expected_uri, expected_data, cert_check=check_cert)


def test_is_testrun_available(api_client, tr_plugin):
    """ Test of method `is_testrun_available` """
    tr_plugin.testrun_id = 100

    api_client.send_get.return_value = {'is_completed': False}
    assert tr_plugin.is_testrun_available() is True

    api_client.send_get.return_value = {'error': 'An error occured'}
    assert tr_plugin.is_testrun_available() is False

    api_client.send_get.return_value = {'is_completed': True}
    assert tr_plugin.is_testrun_available() is False


def test_is_testplan_available(api_client, tr_plugin):
    """ Test of method `is_testplan_available` """
    tr_plugin.testplan_id = 100

    api_client.send_get.return_value = {'is_completed': False}
    assert tr_plugin.is_testplan_available() is True

    api_client.send_get.return_value = {'error': 'An error occured'}
    assert tr_plugin.is_testplan_available() is False

    api_client.send_get.return_value = {'is_completed': True}
    assert tr_plugin.is_testplan_available() is False


def test_get_available_testruns(api_client, tr_plugin):
    """ Test of method `get_available_testruns` """
    testplan_id = 100
    api_client.send_get.return_value = TESTPLAN
    assert tr_plugin.get_available_testruns(testplan_id) == [59, 61]
