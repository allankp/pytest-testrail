from datetime import datetime
import pytest


PYTEST_TO_TESTRAIL_STATUS = {
    "passed": 1,
    "failed": 5,
    "skipped": 2,
}

DT_FORMAT = '%d-%m-%Y %H:%M:%S'

TESTRAIL_PREFIX = 'testrail'
SUITE_PREFIX = 'suite_testrail'

ADD_RESULTS_URL = 'add_results_for_cases/{}/'
ADD_TESTRUN_URL = 'add_run/{}'
ADD_TESTPLAN_URL = 'add_plan/{}'


def testrail(*ids):
    """
    Decorator to mark tests with testcase ids.

    ie. @testrail('C123', 'C12345')

    :return pytest.mark:
    """
    return pytest.mark.testrail(ids=ids)


def suite_testrail(suite_id, *ids):
    """
    Decorator to mark cases with the suite id and test case
    i.e. @suite_testrail('S12', 'C123')
    :param id:
    :return: pytest.mark
    """
    return pytest.mark.suite_testrail(suite_id=suite_id, ids=ids)


def get_test_outcome(outcome):
    """
    Return numerical value of test outcome.

    :param str outcome: pytest reported test outcome value.
    :returns: int relating to test outcome.
    """
    return PYTEST_TO_TESTRAIL_STATUS[outcome]


def testrun_name():
    """Returns testrun name with timestamp"""
    now = datetime.utcnow()
    return 'Automated Run {}'.format(now.strftime(DT_FORMAT))


def clean_test_ids(test_ids):
    """
    Clean pytest marker containing testrail testcase ids.

    :param list test_ids: list of test_ids.
    :return list ints: contains list of test_ids as ints.
    """
    return map(int, [test_id.upper().replace('C', '') for test_id in test_ids])


def clean_suite_ids(test_id):
    """
    Clean pytest marker containing testrail testcase ids.

    :param test_id
    :return an int
    """
    return int(test_id.upper().replace('S', ''))


def get_testrail_keys(items):
    """Return TestRail ids from pytests markers"""
    testcaseids = []
    for item in items:
        if item.get_marker(TESTRAIL_PREFIX):
            testcaseids.extend(
                clean_test_ids(
                    item.get_marker(TESTRAIL_PREFIX).kwargs.get('ids')
                )
            )
    return testcaseids


def get_testrail_suite_and_keys(items):
    """Return TestRail ids from pytests markers"""
    suite_dict = {}
    for item in items:
        if item.get_marker(SUITE_PREFIX):
            _suite_id = clean_suite_ids(
                item.get_marker(SUITE_PREFIX).kwargs.get('suite_id')
            )
            if not suite_dict.has_key(_suite_id):
                suite_dict[_suite_id] = []
            # now get the test case numbers
            suite_dict[_suite_id].extend(
                clean_test_ids(
                    item.get_marker(SUITE_PREFIX).kwargs.get('ids')
                )
            )
    return suite_dict


class TestRailPlugin(object):
    def __init__(
            self, client, assign_user_id, project_id, suite_id, cert_check, tr_name, use_testplan=False):
        self.assign_user_id = assign_user_id
        self.cert_check = cert_check
        self.client = client
        self.project_id = project_id
        self.use_testplan = use_testplan
        if self.use_testplan:
            self.results = {}
        else:
            self.results = []
        self.suite_id = suite_id
        self.testrun_id = 0
        self.testrun_ids = {}
        self.testrun_name = tr_name


    # pytest hooks

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        if self.testrun_name is None:
            self.testrun_name = testrun_name()

        if self.use_testplan:
            tp_keys = get_testrail_suite_and_keys(items)
            self.create_test_plan(
                self.assign_user_id,
                self.project_id,
                self.testrun_name,
                tp_keys
            )
        else:
            tr_keys = get_testrail_keys(items)
            self.create_test_run(
                self.assign_user_id,
                self.project_id,
                self.suite_id,
                self.testrun_name,
                tr_keys
            )

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        rep = outcome.get_result()
        if item.get_marker(TESTRAIL_PREFIX):
            testcaseids = item.get_marker(TESTRAIL_PREFIX).kwargs.get('ids')

            if rep.when == 'call' and testcaseids:
                self.add_result(
                    clean_test_ids(testcaseids),
                    get_test_outcome(outcome.result.outcome)
                )
        elif item.get_marker(SUITE_PREFIX):
            _suite_id = item.get_marker(SUITE_PREFIX).kwargs.get('suite_id')
            testcaseids = item.get_marker(SUITE_PREFIX).kwargs.get('ids')
            if rep.when == 'call' and testcaseids:
                self.add_suite_result(
                    clean_suite_ids(_suite_id),
                    clean_test_ids(testcaseids),
                    get_test_outcome(outcome.result.outcome)
                )

    def pytest_sessionfinish(self, session, exitstatus):
        if self.use_testplan:
            for suite, results in self.results.iteritems():
                data = {'results': results}
                response = self.client.send_post(
                    ADD_RESULTS_URL.format(self.testrun_ids[int(suite)]),
                    data,
                    self.cert_check
                )

                for key, _ in response[0].iteritems():
                    if key == 'error':
                        print('Failed to populate testrun: {}'.format(response))
                    else:
                        pass
        else:
            data = {'results': self.results}
            if data['results']:
                self.client.send_post(
                    ADD_RESULTS_URL.format(self.testrun_id),
                    data,
                    self.cert_check
                )

    # plugin

    def add_result(self, test_ids, status):
        """
        Add a new result to results dict to be submitted at the end.

        :param list test_id: list of test_ids.
        :param int status: status code of test (pass or fail).
        """
        for test_id in test_ids:
            data = {
                'case_id': test_id,
                'status_id': status,
            }
            self.results.append(data)

    def add_suite_result(self, suite_id, test_ids, status):
        """
        Add a new result to results dict to be submitted at the end.

        :param list test_id: list of test_ids.
        :param int status: status code of test (pass or fail).
        """
        for test_id in test_ids:
            data = {
                'case_id': test_id,
                'status_id': status,
            }
            if not self.results.has_key(suite_id):
                self.results[suite_id] = []
            self.results[suite_id].append(data)

    def create_test_run(
            self, assign_user_id, project_id, suite_id, testrun_name, tr_keys):
        """
        Create testrun with ids collected from markers.

        :param list items: collected testrail ids.
        """
        data = {
            'suite_id': suite_id,
            'name': testrun_name,
            'assignedto_id': assign_user_id,
            'include_all': False,
            'case_ids': tr_keys,
        }

        response = self.client.send_post(
            ADD_TESTRUN_URL.format(project_id),
            data,
            self.cert_check
        )
        for key, _ in response.items():
            if key == 'error':
                print('Failed to create testrun: {}'.format(response))
            else:
                self.testrun_id = response['id']

    def create_test_plan(self, assign_user_id, project_id, testrun_name, suites_and_cases):
        """
        Create testrun with the suites and ids
        :param assign_user_id:
        :param project_id:
        :param testrun_name:
        :param data:
        :return:
        """
        data = {
            "name": testrun_name,
        }
        # add the assigned to for each section, and set include_all to false
        entries = []
        for id, lst in suites_and_cases.iteritems():
            e = {
                "suite_id": id,
                "assignedto_id": assign_user_id,
                "include_all": False,
                "case_ids": suites_and_cases[id],
            }
            entries.append(e)

        data['entries'] = entries

        response = self.client.send_post(
            ADD_TESTPLAN_URL.format(project_id),
            data,
            self.cert_check
        )
        for key, _ in response.items():
            if key == 'error':
                print('Failed to create testrun: {}'.format(response))
            else:
                # now we have to record run id by suite
                for e in response['entries']:
                    # there can be multiple runs, but we won't worry about that right now.
                    self.testrun_ids[e['runs'][0]['suite_id']] = e['runs'][0]['id']
                break
