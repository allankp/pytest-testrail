# -*- coding: UTF-8 -*-
from datetime import datetime
from freezegun import freeze_time
from mock import call, create_autospec
import pytest
from pytest_testrail import plugin
from pytest_testrail.plugin import PyTestRailPlugin, TESTRAIL_TEST_STATUS
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
DESCRIPTION = 'This is a test description'
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
    return PyTestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, False, True, TR_NAME, DESCRIPTION, version='1.0.0.0', 
                            milestone_id=MILESTONE_ID)


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
    items = plugin.get_testrail_keys(pytest_test_items)
    assert list(items[0][1]) == [1234, 5678]
    assert list(items[1][1]) == [8765, 4321]


def test_add_result(tr_plugin):
    status = TESTRAIL_TEST_STATUS["passed"]
    tr_plugin.add_result([1, 2], status, comment='ERROR!', duration=3600, defects='PF-456')

    expected_results = [
        {
            'case_id': 1,
            'status_id': status,
            'comment': "ERROR!",
            'duration': 3600,
            'defects': 'PF-456'
        },
        {
            'case_id': 2,
            'status_id': status,
            'comment': "ERROR!",
            'duration': 3600,
            'defects': 'PF-456'
        }
    ]

    assert tr_plugin.results == expected_results


def test_pytest_runtest_makereport(pytest_test_items, tr_plugin, testdir):
    # --------------------------------
    # This part of code is a little tricky: it fakes the execution of pytest_runtest_makereport (generator)
    # by artificially send a stub object (Outcome)
    class Outcome:
        def __init__(self):
            testdir.makepyfile(PYTEST_FILE)
            self.result = testdir.runpytest()
            setattr(self.result, "when", "call")
            setattr(self.result, "longrepr", "An error")
            setattr(self.result, "outcome", "failed")
            self.result.duration = 2

        def get_result(self):
            return self.result

    outcome = Outcome()
    f = tr_plugin.pytest_runtest_makereport(pytest_test_items[0], None)
    f.send(None)
    try:
        f.send(outcome)
    except StopIteration:
        pass
    # --------------------------------

    expected_results = [
        {
            'case_id': 1234,
            'status_id': TESTRAIL_TEST_STATUS["failed"],
            'comment': "An error",
            'duration': 2,
            'defects': None
        },
        {
            'case_id': 5678,
            'status_id': TESTRAIL_TEST_STATUS["failed"],
            'comment': "An error",
            'duration': 2,
            'defects': None
        }
    ]
    assert tr_plugin.results == expected_results


def test_pytest_sessionfinish(api_client, tr_plugin):
    tr_plugin.results = [
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["failed"], 'duration': 2.6, 'defects':'PF-516'},
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'comment': "An error", 'duration': 0.1, 'defects':None},
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'duration': 2.6, 'defects': ['PF-517', 'PF-113']}
    ]
    tr_plugin.testrun_id = 10

    tr_plugin.pytest_sessionfinish(None, 0)

    expected_data = {'results': [
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["failed"], 'defects':'PF-516', 'version': '1.0.0.0', 'elapsed': '3s'},
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'defects':['PF-517', 'PF-113'], 'version': '1.0.0.0', 'elapsed': '3s'},
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'defects':None, 'version': '1.0.0.0', 'elapsed': '1s',
         'comment': "# Pytest result: #\n    An error"}
    ]}

    api_client.send_post.assert_any_call(plugin.ADD_RESULTS_URL.format(tr_plugin.testrun_id), expected_data,
                                         cert_check=True)


def test_pytest_sessionfinish_testplan(api_client, tr_plugin):
    tr_plugin.results = [
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'comment': "An error", 'duration': 0.1, 'defects':None,},
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'duration': 2.6, 'defects':None,}
    ]
    tr_plugin.testplan_id = 100
    tr_plugin.testrun_id = 0

    api_client.send_get.return_value = TESTPLAN
    tr_plugin.pytest_sessionfinish(None, 0)
    expected_data = {'results': [
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'version': '1.0.0.0', 'elapsed': '3s', 'defects':None,},
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'version': '1.0.0.0', 'elapsed': '1s', 'defects':None,
         'comment': "# Pytest result: #\n    An error"}
    ]}
    print(api_client.send_post.call_args_list)

    api_client.send_post.assert_any_call(plugin.ADD_RESULTS_URL.format(59, 1234),
                                         expected_data, cert_check=True)
    api_client.send_post.assert_any_call(plugin.ADD_RESULTS_URL.format(61, 5678),
                                         expected_data, cert_check=True)


@pytest.mark.parametrize('include_all', [True, False])
def test_create_test_run(api_client, tr_plugin, include_all):
    expected_tr_keys = [3453, 234234, 12]
    expect_name = 'testrun_name'

    tr_plugin.create_test_run(ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, include_all, expect_name, expected_tr_keys,
                              MILESTONE_ID, DESCRIPTION)

    expected_uri = plugin.ADD_TESTRUN_URL.format(PROJECT_ID)
    expected_data = {
        'suite_id': SUITE_ID,
        'name': expect_name,
        'description': DESCRIPTION,
        'assignedto_id': ASSIGN_USER_ID,
        'include_all': include_all,
        'case_ids': expected_tr_keys,
        'milestone_id': MILESTONE_ID
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


def test_close_test_run(api_client, tr_plugin):
    tr_plugin.results = [
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["failed"], 'duration': 2.6, 'defects':None},
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'comment': "An error", 'duration': 0.1, 'defects':None},
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'duration': 2.6, 'defects':None}
    ]
    tr_plugin.testrun_id = 10
    tr_plugin.close_on_complete = True
    tr_plugin.pytest_sessionfinish(None, 0)

    expected_uri = plugin.CLOSE_TESTRUN_URL.format(tr_plugin.testrun_id)
    api_client.send_post.call_args_list[1] = call(expected_uri, {}, cert_check=True)


def test_close_test_plan(api_client, tr_plugin):
    tr_plugin.results = [
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'comment': "An error", 'duration': 0.1, 'defects':None},
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'duration': 2.6, 'defects':None}
    ]
    tr_plugin.testplan_id = 100
    tr_plugin.testrun_id = 0
    tr_plugin.close_on_complete = True

    api_client.send_get.return_value = TESTPLAN
    tr_plugin.pytest_sessionfinish(None, 0)

    expected_uri = plugin.CLOSE_TESTPLAN_URL.format(tr_plugin.testplan_id)
    api_client.send_post.call_args_list[1] = call(expected_uri, {}, cert_check=True)


def test_dont_publish_blocked(api_client):
    """ Case: one test is blocked"""
    my_plugin = PyTestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID, SUITE_ID, False, True, TR_NAME,
                                 version='1.0.0.0',
                                 publish_blocked=False
                                 )

    my_plugin.results = [
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'defects': None},
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'defects': None}
    ]
    my_plugin.testrun_id = 10

    api_client.send_get.return_value = [
        {'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'defects':None},
        {'case_id': 5678, 'status_id': TESTRAIL_TEST_STATUS["passed"], 'defects':None}
    ]

    my_plugin.pytest_sessionfinish(None, 0)

    api_client.send_get.assert_called_once_with(plugin.GET_TESTS_URL.format(my_plugin.testrun_id),
                                                cert_check=True)
    expected_uri = plugin.ADD_RESULTS_URL.format(my_plugin.testrun_id)
    expected_data = {'results': [{'case_id': 1234, 'status_id': TESTRAIL_TEST_STATUS["blocked"], 'version': '1.0.0.0'}]}
    len(api_client.send_post.call_args_list) == 1
    api_client.send_post.call_args_list[0] == call(expected_uri, expected_data, cert_check=True)


def test_skip_missing_only_one_test(api_client, pytest_test_items):
    my_plugin = PyTestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID,
                                 SUITE_ID, False, True, TR_NAME,
                                 run_id=10,
                                 version='1.0.0.0',
                                 publish_blocked=False,
                                 skip_missing=True)

    api_client.send_get.return_value = [
        {"case_id": 1234}, {"case_id": 5678}
    ]
    my_plugin.is_testrun_available = lambda: True

    my_plugin.pytest_collection_modifyitems(None, None, pytest_test_items)

    assert not pytest_test_items[0].get_closest_marker('skip')
    assert pytest_test_items[1].get_closest_marker('skip')


def test_skip_missing_correlation_tests(api_client, pytest_test_items):
    my_plugin = PyTestRailPlugin(api_client, ASSIGN_USER_ID, PROJECT_ID,
                                 SUITE_ID, False, True, TR_NAME,
                                 run_id=10,
                                 version='1.0.0.0',
                                 publish_blocked=False,
                                 skip_missing=True)

    api_client.send_get.return_value = [
        {"case_id": 1234}, {"case_id": 8765}
    ]
    my_plugin.is_testrun_available = lambda: True

    my_plugin.pytest_collection_modifyitems(None, None, pytest_test_items)

    assert not pytest_test_items[0].get_closest_marker('skip')
    assert not pytest_test_items[1].get_closest_marker('skip')
