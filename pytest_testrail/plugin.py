from datetime import datetime
import pytest
import re
import warnings

PYTEST_TO_TESTRAIL_STATUS = {
    "passed": 1,
    "failed": 5,
    "untested": 3,
    "skipped": 2,
}

DT_FORMAT = '%d-%m-%Y %H:%M:%S'

TESTRAIL_PREFIX = 'testrail'

ADD_RESULTS_URL = 'add_results_for_cases/{}/'
ADD_TESTRUN_URL = 'add_run/{}'
GET_CASE = 'get_case/{}'


class DeprecatedTestDecorator(DeprecationWarning):
    pass


warnings.simplefilter(action='once', category=DeprecatedTestDecorator, lineno=0)


class pytestrail(object):
    '''
    An alternative to using the testrail function as a decorator for test cases, since py.test may confuse it as a test
    function since it has the 'test' prefix
    '''

    @staticmethod
    def case(*ids):
        """
        Decorator to mark tests with testcase ids.

        ie. @pytestrail.case('C123', 'C12345')

        :return pytest.mark:
        """
        return pytest.mark.testrail(ids=ids)


def testrail(*ids):
    """
    Decorator to mark tests with testcase ids.

    ie. @testrail('C123', 'C12345')

    :return pytest.mark:
    """
    deprecation_msg = ('pytest_testrail: the @testrail decorator is deprecated and will be removed. Please use the '
                       '@pytestrail.case decorator instead.')
    warnings.warn(deprecation_msg, DeprecatedTestDecorator)
    return pytestrail.case(*ids)


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
    return map(int, [re.search('(?P<test_id>[0-9]+$)', test_id).groupdict().get('test_id') for test_id in test_ids])


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


class PyTestRailPluginSuper(object):
    def __init__(self, client, cert_check):
        self.results = dict()
        self.cert_check = cert_check
        self.client = client
        self.testrun_id = 0

    def add_result(self, test_ids, status, comment):
        """
        Add a new result to results dict to be submitted at the end.

        :param list test_id: list of test_ids.
        :param int status: status code of test (pass or fail).
        """
        for test_id in test_ids:
            data = {
                'case_id': test_id,
                'comment': comment,
                'status_id': status
            }

            if self.results.__contains__(test_id):
                if not self.results[test_id]['status_id'] == 5:
                    self.results[test_id]['status_id'] = status
                self.results[test_id]['comment'] += "\n{}\n{}".format(30 * "-", data['comment'])
            else:
                self.results[test_id] = data

    def get_test_results(self, test_id):
        test_results = self.client.send_get("get_results/{}".format(test_id), cert_check=self.cert_check)
        return test_results

    def get_lastest_test_status(self, test_results):
        if test_results:
            return test_results[0]['status_id']
        else:
            return PYTEST_TO_TESTRAIL_STATUS['untested']

    def get_case(self, case_id):
        response = self.client.send_get(
            GET_CASE.format(case_id)
        )

        return response

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        rep = outcome.get_result()

        if item.get_marker(TESTRAIL_PREFIX):
            comment = str(item.repr_failure(call.excinfo)) if call.excinfo else ""
            testcaseids = item.get_marker(TESTRAIL_PREFIX).kwargs.get('ids')

            if rep.when == 'call' and testcaseids:
                self.add_result(
                    clean_test_ids(testcaseids),
                    get_test_outcome(outcome.result.outcome),
                    comment)

    def pytest_sessionfinish(self, session, exitstatus):
        data = {'results': self.results}
        if data['results']:
            self.client.send_post(
                ADD_RESULTS_URL.format(self.testrun_id),
                data,
                cert_check=self.cert_check
            )



class PyTestRailPlugin(PyTestRailPluginSuper):

    def __init__(self, client, assign_user_id, project_id, suite_id, cert_check, tr_name):
        PyTestRailPluginSuper.__init__(self, client, cert_check)
        self.assign_user_id = assign_user_id
        self.project_id = project_id
        self.suite_id = suite_id
        self.testrun_name = tr_name

    # pytest hooks

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        tr_keys = get_testrail_keys(items)
        if self.testrun_name is None:
            self.testrun_name = testrun_name()

        self.create_test_run(
            self.assign_user_id,
            self.project_id,
            self.suite_id,
            self.testrun_name,
            tr_keys
        )

    # plugin


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
            cert_check=self.cert_check
        )
        for key, _ in response.items():
            if key == 'error':
                print('Failed to create testrun: {}'.format(response))
            else:
                self.testrun_id = response['id']


class PyTestRailPlugin2(PyTestRailPluginSuper):
    def __init__(self, client, test_run_id, cert_check, type_skip_list):
        PyTestRailPluginSuper.__init__(self, client, cert_check)
        # testrail testrun id
        self.testrun_id = test_run_id
        # testrail statuses you need to skip
        self.type_skip_list = type_skip_list

    # pytest hooks
    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, config, items):
        # get all tests in testrun testrail
        tests_list = self.get_test_run()
        # list tests for run
        run = set()
        # list tests for skip
        skip = set()
        # dict with all tests pytest marks
        item_dict = dict()
        for item in items:
            testcaseids = clean_test_ids(item.get_marker(TESTRAIL_PREFIX).kwargs.get('ids')) if item.get_marker(
                TESTRAIL_PREFIX) else None

            # add in dict "item_dict" all tests testrail marks
            if testcaseids:
                for test_case_id in testcaseids:
                    if item_dict.__contains__(test_case_id):
                        item_dict[test_case_id] += [item]
                    else:
                        item_dict[test_case_id] = [item]

        for case in tests_list:
            # get all results for test in testrail
            test_results = self.get_test_results(case['test_id'])
            # get the latest test status in testrail
            last_status_test = self.get_lastest_test_status(test_results)

            # if testrail_case_id is contained in item_dict and test_last_status dont need skip, add in dict run, else add in dict skip
            if (case['case_id'] in item_dict.keys()):
                if last_status_test not in self.type_skip_list:
                    for test_case_id in item_dict[case['case_id']]:
                        run.add(test_case_id)
                else:
                    for test_case_id in item_dict[case['case_id']]:
                        skip.add(test_case_id)

        # running only the necessary tests and deselected all missed tests
        items[:] = run
        if skip:
            config.hook.pytest_deselected(items=list(skip))

    def get_test_run(self):

        case = self.client.send_get("get_tests/{}".format(self.testrun_id), cert_check=self.cert_check)
        test_cases_id_list = []
        for test in case:
            test_cases_id_list.append({"case_id": test['case_id'], "test_id": test['id']})
        return test_cases_id_list
