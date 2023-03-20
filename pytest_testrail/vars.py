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
TESTRAIL_SUITES_PREFIX = "testrail_suites"
ADD_RESULTS_URL = 'add_results_for_cases/{}'
ADD_TESTRUN_URL = 'add_run/{}'
ADD_TESTPLAN_ENTRY_URL = 'add_plan_entry/{}'
ADD_TESTPLAN_URL = 'add_plan/{}'
CLOSE_TESTRUN_URL = 'close_run/{}'
CLOSE_TESTPLAN_URL = 'close_plan/{}'
GET_TESTRUN_URL = 'get_run/{}'
GET_TESTPLAN_URL = 'get_plan/{}'
GET_TESTS_URL = 'get_tests/{}'
GET_TESTCASES_URL = 'get_cases/{}&suite_id={}&limit=99999'
GET_SUITES_URL = 'get_suites/{}'
UPDATE_RUN_URL = 'update_run/{}'
UPDATE_TESTPLAN_ENTRY = "/update_plan_entry/{}/{}"

COMMENT_SIZE_LIMIT = 4000
