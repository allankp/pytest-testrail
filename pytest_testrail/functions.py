import re
import warnings

import pytest
from datetime import datetime
from pytest_testrail.vars import PYTEST_TO_TESTRAIL_STATUS, DT_FORMAT, TESTRAIL_PREFIX, TESTRAIL_SUITES_PREFIX


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
    def suite(*ids):
        """
        Decorator to mark tests with testcase ids.

        ie. @pytestrail.case('C123', 'C12345')

        :return pytest.mark:
        """
        return pytest.mark.testrail_suites(ids=ids)

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


def testplan_name():
    """Returns testrun name with timestamp"""
    now = datetime.utcnow()
    return 'Automated Plan Entry {}'.format(now.strftime(DT_FORMAT))



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

def clean_suite_ids(suite_ids):
    """
        Clean pytest marker containing testrail suite ids.

        :param list suite_ids: list of suite_ids.
        :return list ints: contains list of suite_ids as ints.
        """
    return [int(re.search('(?P<suite_id>[0-9]+$)', suite_id).groupdict().get('suite_id')) for suite_id in suite_ids]

def get_case_list(tests: list):
    """
    Return list of case ids from testrun
    :param list tests: list of tests from get_tests
    """
    testcaseids = []
    for test in tests or []:
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

def get_testrail_suite_ids(items)-> list:
    suite_ids = []
    for item in items:
        if item.get_closest_marker(TESTRAIL_SUITES_PREFIX):
            suite_ids.append(
                (
                    item,
                    clean_suite_ids(item.get_closest_marker(TESTRAIL_SUITES_PREFIX).kwargs.get('ids'))
                )
            )

    return suite_ids

def filter_publish_results(results, ignore_cases):
    clear_results = []
    test_case_ids_list = []
    for result in results:
        if int(result['case_id']) not in ignore_cases:
            clear_results.append(result)
            test_case_ids_list.append(str(result['case_id']))
    return clear_results, test_case_ids_list

def get_suite_by_case(case, suites):
    for suite, cases in suites.items():
        if case in cases:
            return suite
    return 0