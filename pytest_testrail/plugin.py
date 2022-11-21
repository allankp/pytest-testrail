# -*- coding: UTF-8 -*-
from datetime import datetime
from operator import itemgetter

import pytest
import re
import warnings

from pyparsing import unicode

from pytest_testrail.TestrailModel import TestRailModel

# Reference: http://docs.gurock.com/testrail-api2/reference-statuses
TESTRAIL_TEST_STATUS = {
    "passed": 1,
    "blocked": 2,
    "untested": 3,
    "retest": 4,
    "failed": 5
}

PYTEST_TO_TESTRAIL_STATUS = {
    "passed": TESTRAIL_TEST_STATUS["passed"],
    "failed": TESTRAIL_TEST_STATUS["failed"],
    "skipped": TESTRAIL_TEST_STATUS["blocked"],
}

DT_FORMAT = '%d-%m-%Y %H:%M:%S'

TESTRAIL_PREFIX = 'testrail'
TESTRAIL_DEFECTS_PREFIX = 'testrail_defects'
ADD_RESULTS_URL = 'add_results_for_cases/{}'
ADD_TESTRUN_URL = 'add_run/{}'
CLOSE_TESTRUN_URL = 'close_run/{}'
CLOSE_TESTPLAN_URL = 'close_plan/{}'
GET_TESTRUN_URL = 'get_run/{}'
GET_TESTPLAN_URL = 'get_plan/{}'
GET_TESTS_URL = 'get_tests/{}'
UPDATE_RUN_URL = 'update_run/{}'

COMMENT_SIZE_LIMIT = 4000


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

    @staticmethod
    def defect(*defect_ids):
        """
                Decorator to mark defects with defect ids.

                ie. @pytestrail.defect('PF-513', 'BR-3255')

                :return pytest.mark:
                """
        return pytest.mark.testrail_defects(defect_ids=defect_ids)


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


def is_xdist_worker(config):
    """True if the code running the given pytest.config object is running in a xdist master
    node or not running xdist at all.
    """
    return hasattr(config, 'workerinput')


def clean_test_ids(test_ids):
    """
    Clean pytest marker containing testrail testcase ids.

    :param list test_ids: list of test_ids.
    :return list ints: contains list of test_ids as ints.
    """
    return [int(re.search('(?P<test_id>[0-9]+$)', test_id).groupdict().get('test_id')) for test_id in test_ids]


def clean_test_defects(defect_ids):
    """
        Clean pytest marker containing testrail defects ids.

        :param list defect_ids: list of defect_ids.
        :return list ints: contains list of defect_ids as ints.
        """
    return [(re.search('(?P<defect_id>.*)', defect_id).groupdict().get('defect_id')) for defect_id in defect_ids]


def get_case_list(tests: list):
    """
    Return list of case ids from testrun
    :param list tests: list of tests from get_tests
    """
    testcaseids = []
    for test in tests:
        testcaseids.append(test['case_id'])
    return testcaseids


def get_testrail_keys(items):
    """Return Tuple of Pytest nodes and TestRail ids from pytests markers"""
    testcaseids = []
    for item in items:
        if item.get_closest_marker(TESTRAIL_PREFIX):
            testcaseids.append(
                (
                    item,
                    clean_test_ids(
                        item.get_closest_marker(TESTRAIL_PREFIX).kwargs.get('ids')
                    )
                )
            )
    return testcaseids


class TestrailActions:
    def __init__(self, testrail_data: TestRailModel):
        self.testrail_data = testrail_data

    def add_result(self, test_id, status, comment='', defects=None, duration=0, test_parametrize=None):
        """
        Add a new result to results dict to be submitted at the end.

        :param list test_parametrize: Add test parametrize to test result
        :param defects: Add defects to test result
        # :param list test_ids: list of test_ids.
        :param int status: status code of test (pass or fail).
        :param comment: None or a failure representation.
        :param duration: Time it took to run just the test.
        """

        data = {
            'case_id': test_id,
            'status_id': status,
            'comment': comment,
            'duration': duration,
            'defects': defects,
            'test_parametrize': test_parametrize
        }
        return data

    def _add_results(self, testrun_id, results):
        """
        Add results one by one to improve errors handling.
        :param testrun_id: Id of the testrun to feed

        """
        # unicode converter for compatibility of python 2 and 3
        try:
            converter = unicode
        except NameError:
            converter = lambda s, c: str(bytes(s, "utf-8"), c)
        # Results are sorted by 'case_id' and by 'status_id' (worst result at the end)
        # Comment sort by status_id due to issue with pytest-rerun failures,
        # for details refer to issue https://github.com/allankp/pytest-testrail/issues/100
        # self.results.sort(key=itemgetter('status_id'))
        results.sort(key=itemgetter('case_id'))

        # Manage case of "blocked" testcases
        if self.testrail_data.publish_blocked is False:
            print('[{}] Option "Don\'t publish blocked testcases" activated'.format(TESTRAIL_PREFIX))
            blocked_tests_list = [
                test.get('case_id') for test in self.get_tests(testrun_id)
                if test.get('status_id') == TESTRAIL_TEST_STATUS["blocked"]
            ]
            print('[{}] Blocked testcases excluded: {}'.format(TESTRAIL_PREFIX,
                                                               ', '.join(str(elt) for elt in blocked_tests_list)))
            results = [result for result in results if result.get('case_id') not in blocked_tests_list]

        # prompt enabling include all test cases from test suite when creating test run
        if self.testrail_data.include_all:
            print('[{}] Option "Include all testcases from test suite for test run" activated'.format(TESTRAIL_PREFIX))

        # Publish results
        data = {'results': []}
        for result in results:
            entry = {'status_id': result['status_id'], 'case_id': result['case_id'], 'defects': result['defects']}
            if self.testrail_data.version:
                entry['version'] = self.testrail_data.version
            comment = result.get('comment', '')
            test_parametrize = result.get('test_parametrize', '')
            entry['comment'] = u''
            if test_parametrize:
                entry['comment'] += u"# Test parametrize: #\n"
                entry['comment'] += str(test_parametrize) + u'\n\n'
            if comment:
                if self.testrail_data.custom_comment:
                    entry['comment'] += self.testrail_data.custom_comment + '\n'
                # Indent text to avoid string formatting by TestRail. Limit size of comment.
                entry['comment'] += u"# Pytest result: #\n"
                entry['comment'] += u'Log truncated\n...\n' if len(str(comment)) > COMMENT_SIZE_LIMIT else u''
                entry['comment'] += u"    " + converter(str(comment), "utf-8")[-COMMENT_SIZE_LIMIT:].replace('\n',
                                                                                                             '\n    ')  # noqa                                                                                               '\n    ')  # noqa
            elif comment == '':
                entry['comment'] = self.testrail_data.custom_comment
            duration = result.get('duration')
            if duration:
                duration = 1 if (duration < 1) else int(round(duration))  # TestRail API doesn't manage milliseconds
                entry['elapsed'] = str(duration) + 's'
            data['results'].append(entry)

        response = self.testrail_data.client.send_post(
            ADD_RESULTS_URL.format(testrun_id),
            data,
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Info: Testcases not published for following reason: "{}"'.format(TESTRAIL_PREFIX, error))

    def publish_results(self, testrail_data: TestRailModel = None, results: list = None):
        print('[{}] Start publishing'.format(TESTRAIL_PREFIX))

        if results:
            tests_list = list(set([str(result['case_id']) for result in results]))
            print('[{}] Testcases to publish: {}'.format(TESTRAIL_PREFIX, ', '.join(tests_list)))

            if testrail_data.testrun_id:
                self._add_results(self.testrail_data.testrun_id, results)
            elif self.testrail_data.testplan_id:
                testruns = self.get_available_testruns(self.testrail_data.testplan_id)
                print('[{}] Testruns to update: {}'.format(TESTRAIL_PREFIX, ', '.join([str(elt) for elt in testruns])))
                for testrun_id in testruns:
                    self._add_results(testrun_id, results)
            else:
                print('[{}] No data published'.format(TESTRAIL_PREFIX))

            if self.testrail_data.close_on_complete and self.testrail_data.testrun_id:
                self.close_test_run(self.testrail_data.testrun_id)
            elif self.testrail_data.close_on_complete and self.testrail_data.testplan_id:
                self.close_test_plan(self.testrail_data.testplan_id)
        print('[{}] End publishing'.format(TESTRAIL_PREFIX))

    def create_test_run(self, assign_user_id, project_id, suite_id, include_all,
                        testrun_name, tr_keys, milestone_id, description=''):
        """
        Create testrun with ids collected from markers.

        :param tr_keys: collected testrail ids.
        """
        data = {
            'suite_id': suite_id,
            'name': testrun_name,
            'description': description,
            'assignedto_id': assign_user_id,
            'include_all': include_all,
            'case_ids': tr_keys,
            'milestone_id': milestone_id
        }

        response = self.testrail_data.client.send_post(
            ADD_TESTRUN_URL.format(project_id),
            data,
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to create testrun: "{}"'.format(TESTRAIL_PREFIX, error))
            return 0
        else:
            self.testrail_data.testrun_id = response['id']
            print('[{}] New testrun created with name "{}" and ID={}'.format(TESTRAIL_PREFIX,
                                                                             testrun_name,
                                                                             self.testrail_data.testrun_id))
            return response['id']

    def update_testrun(self, testrun_id: int, tr_keys: list, save_previous: bool = True) -> None:
        """
        Updates an existing test run
        :param testrun_id: testrun id
        :param tr_keys: collected testrail ids
        :param save_previous: collected testrail ids
        """
        current_tests = []
        if save_previous:
            current_tests = get_case_list(self.get_tests(run_id=testrun_id))

        data = {
            'case_ids': list(set(tr_keys + current_tests)),
        }

        response = self.testrail_data.client.send_post(
            UPDATE_RUN_URL.format(testrun_id),
            data,
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to update testrun: "{}"'.format(TESTRAIL_PREFIX, error))
        else:
            self.testrail_data.testrun_id = response['id']
            print('[{}] Testrun updated with name "{}" and ID={}'.format(TESTRAIL_PREFIX,
                                                                         self.testrail_data.testrun_name,
                                                                         testrun_id))

    def is_testrun_available(self):
        """
        Ask if testrun is available in TestRail.

        :return: True if testrun exists AND is open
        """
        response = self.testrail_data.client.send_get(
            GET_TESTRUN_URL.format(self.testrail_data.testrun_id),
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to retrieve testrun: "{}"'.format(TESTRAIL_PREFIX, error))
            return False

        return response['is_completed'] is False

    def close_test_run(self, testrun_id):
        """
        Closes testrun.

        """
        response = self.testrail_data.client.send_post(
            CLOSE_TESTRUN_URL.format(testrun_id),
            data={},
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to close test run: "{}"'.format(TESTRAIL_PREFIX, error))
        else:
            print('[{}] Test run with ID={} was closed'.format(TESTRAIL_PREFIX, self.testrail_data.testrun_id))

    def close_test_plan(self, testplan_id: int):
        """
        Closes testrun.

        """
        response = self.testrail_data.client.send_post(
            CLOSE_TESTPLAN_URL.format(testplan_id),
            data={},
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to close test plan: "{}"'.format(TESTRAIL_PREFIX, error))
        else:
            print('[{}] Test plan with ID={} was closed'.format(TESTRAIL_PREFIX, self.testrail_data.testplan_id))

    def is_testplan_available(self):
        """
        Ask if testplan is available in TestRail.

        :return: True if testplan exists AND is open
        """
        response = self.testrail_data.client.send_get(
            GET_TESTPLAN_URL.format(self.testrail_data.testplan_id),
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to retrieve testplan: "{}"'.format(TESTRAIL_PREFIX, error))
            return False

        return response['is_completed'] is False

    def get_available_testruns(self, plan_id):
        """
        :return: a list of available testruns associated to a testplan in TestRail.

        """
        testruns_list = []
        response = self.testrail_data.client.send_get(
            GET_TESTPLAN_URL.format(plan_id),
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to retrieve testplan: "{}"'.format(TESTRAIL_PREFIX, error))
        else:
            for entry in response['entries']:
                for run in entry['runs']:
                    if not run['is_completed']:
                        testruns_list.append(run['id'])
        return testruns_list

    def get_tests(self, run_id):
        """
        :return: the list of tests containing in a testrun.

        """
        response = self.testrail_data.client.send_get(
            GET_TESTS_URL.format(run_id),
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to get tests: "{}"'.format(TESTRAIL_PREFIX, error))
            return None
        return response


class PyTestRailPlugin(TestrailActions):

    def __init__(self, client, assign_user_id, project_id, suite_id, include_all, cert_check, tr_name,
                 tr_description='', run_id=0, plan_id=0, version='',
                 close_on_complete=False, publish_blocked=True, skip_missing=False, milestone_id=None,
                 custom_comment=None, user_email=None, user_password=None, tr_url=None):
        self.testrail_data = TestRailModel(assign_user_id=assign_user_id,
                                           cert_check=cert_check,
                                           client=client,
                                           project_id=project_id,
                                           results=[],
                                           suite_id=suite_id,
                                           include_all=include_all,
                                           testrun_name=tr_name,
                                           testrun_description=tr_description,
                                           testrun_id=run_id,
                                           testplan_id=plan_id,
                                           version=version,
                                           close_on_complete=close_on_complete,
                                           publish_blocked=publish_blocked,
                                           skip_missing=skip_missing,
                                           milestone_id=milestone_id,
                                           custom_comment=custom_comment,
                                           tr_keys=[],
                                           user_email=user_email,
                                           user_password=user_password,
                                           tr_url=tr_url
                                           )
        super().__init__(testrail_data=self.testrail_data)
        self.is_use_xdist = False

    # pytest hooks
    def pytest_report_header(self, config, startdir):
        """ Add extra-info in header """
        message = 'pytest-testrail: '
        if self.testrail_data.testplan_id:
            message += 'existing testplan #{} selected'.format(self.testrail_data.testplan_id)
        elif self.testrail_data.testrun_id:
            message += 'existing testrun #{} selected'.format(self.testrail_data.testrun_id)
        else:
            message += 'a new testrun will be created'
        return message

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        items_with_tr_keys = get_testrail_keys(items)
        self.testrail_data.tr_keys = [case_id for item in items_with_tr_keys for case_id in item[1]]
        if self.testrail_data.skip_missing:
            tests_list = [
                test.get('case_id') for test in self.get_tests(self.testrail_data.testrun_id)
            ]
            for item, case_id in items_with_tr_keys:
                if not set(case_id).intersection(set(tests_list)):
                    mark = pytest.mark.skip('Test {} is not present in testrun.'.format(case_id))
                    item.add_marker(mark)
        self.update_testrun(testrun_id=self.testrail_data.testrun_id, tr_keys=list(set(self.testrail_data.tr_keys)))

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """ Collect result and associated testcases (TestRail) of an execution """
        outcome = yield

        rep = outcome.get_result()
        defect_ids = None
        if 'callspec' in dir(item):
            test_parametrize = item.callspec.params
        else:
            test_parametrize = None
        comment = rep.longreprtext if rep.longreprtext else rep.longrepr
        if item.get_closest_marker(TESTRAIL_DEFECTS_PREFIX):
            defect_ids = item.get_closest_marker(TESTRAIL_DEFECTS_PREFIX).kwargs.get('defect_ids')
        if item.get_closest_marker(TESTRAIL_PREFIX):
            testcase_ids = item.get_closest_marker(TESTRAIL_PREFIX).kwargs.get('ids')
            if rep.when == 'call' and testcase_ids:
                for testcase_id in clean_test_ids(testcase_ids):
                    self.testrail_data.results.append(self.add_result(
                        testcase_id,
                        get_test_outcome(outcome.get_result().outcome),
                        comment=comment,
                        duration=rep.duration,
                        defects=str(clean_test_defects(defect_ids)).replace('[', '').replace(']', '').replace("'", '') if defect_ids else None,
                        test_parametrize=test_parametrize))

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        if is_xdist_worker(config=session.config):
            self.testrail_data.testrun_id = session.config.workerinput["test_run_id"]
        else:
            if self.testrail_data.testplan_id and (self.testrail_data.testrun_id and self.is_testrun_available()):
                pass
            elif self.testrail_data.testplan_id and self.is_testplan_available():
                self.testrail_data.testrun_id = 0
            elif self.testrail_data.testrun_id and self.is_testrun_available():
                self.testrail_data.testplan_id = 0
            else:
                if self.testrail_data.testrun_name is None:
                    self.testrail_data.testrun_name = testrun_name()

            if not self.testrail_data.testrun_id:
                self.testrail_data.testrun_id = self.create_test_run(
                    self.testrail_data.assign_user_id,
                    self.testrail_data.project_id,
                    self.testrail_data.suite_id,
                    self.testrail_data.include_all,
                    self.testrail_data.testrun_name,
                    self.testrail_data.tr_keys,
                    self.testrail_data.milestone_id,
                    self.testrail_data.testrun_description
                )

    @pytest.hookimpl(trylast=True, hookwrapper=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """ Publish results in TestRail """
        yield
        if session.config.pluginmanager.get_plugin("xdist"):
            if is_xdist_worker(config=session.config):
                self.is_use_xdist = True
                self.publish_results(testrail_data=self.testrail_data, results=self.testrail_data.results)
            if not self.is_use_xdist and not session.config.getoption("numprocesses"):
                self.publish_results(testrail_data=self.testrail_data, results=self.testrail_data.results)
        else:
            self.publish_results(testrail_data=self.testrail_data, results=self.testrail_data.results)

    def pytest_configure(self, config):
        if config.pluginmanager.hasplugin("xdist"):
            config.pluginmanager.register(NodeAction(self.testrail_data))


class NodeAction(TestrailActions):

    def __init__(self, testrail_data):
        self.testrail_data = testrail_data
        super().__init__(testrail_data=self.testrail_data)

    def pytest_configure_node(self, node):  # type: ignore
        node.workerinput["test_run_id"] = self.testrail_data.testrun_id
