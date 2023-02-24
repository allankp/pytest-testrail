from operator import itemgetter
from pytest_testrail.TestrailModel import TestRailModel
from pytest_testrail.functions import get_case_list, filter_publish_results
from pytest_testrail.vars import TESTRAIL_PREFIX, TESTRAIL_TEST_STATUS, COMMENT_SIZE_LIMIT, ADD_RESULTS_URL, \
    ADD_TESTRUN_URL, ADD_TESTPLAN_ENTRY_URL, UPDATE_RUN_URL, GET_TESTRUN_URL, CLOSE_TESTRUN_URL, CLOSE_TESTPLAN_URL, \
    GET_TESTPLAN_URL, GET_TESTCASES_URL, GET_TESTS_URL, UPDATE_TESTPLAN_ENTRY, ADD_TESTPLAN_URL


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
            results, tests_list = filter_publish_results(results, self.diff_case_ids)

            print('[{}] Testcases to publish: {}'.format(TESTRAIL_PREFIX, ', '.join(set(tests_list))))

            if self.diff_case_ids:
                print(f"[{TESTRAIL_PREFIX}] Not found following testcases in Suite ID={self.testrail_data.suite_id}")
                print(f"[{TESTRAIL_PREFIX}] Testcases will be ignored: {self.diff_case_ids}")

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
            return self.testrail_data.testrun_id

    def create_plan_entry(self, suite_id, testrun_name, assign_user_id, plan_id, include_all, tr_keys, description=''):
        data = {
            'suite_id': suite_id,
            'name': testrun_name,
            'description': description,
            'assignedto_id': assign_user_id,
            'include_all': include_all,
            'case_ids': tr_keys
        }

        response = self.testrail_data.client.send_post(
            ADD_TESTPLAN_ENTRY_URL.format(plan_id),
            data,
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to create testplan entry: "{}"'.format(TESTRAIL_PREFIX, error))
            return 0
        else:
            self.testrail_data.testplan_entry_id = response['id']
            self.testrail_data.testrun_id = response['runs'][0]['id']
            print('[{}] New TestPlan entry created with name "{}" and ID={}, entry_id={}'
                  .format(TESTRAIL_PREFIX,
                          testrun_name,
                          self.testrail_data.testrun_id,
                          self.testrail_data.testplan_entry_id))

            return self.testrail_data.testrun_id

    def create_plan(self, project_id, plan_name, milestone_id, description=''):
        data = {
            'name': plan_name,
            'description': description,
            'milestone_id': milestone_id,
        }

        response = self.testrail_data.client.send_post(
            ADD_TESTPLAN_URL.format(project_id),
            data,
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to create test plan: "{}"'.format(TESTRAIL_PREFIX, error))
            return 0
        else:
            self.testrail_data.testplan_id = response['id']
            print('[{}] New test plan created with name "{}" and ID={}'.format(TESTRAIL_PREFIX,
                                                                               plan_name,
                                                                               self.testrail_data.testplan_id))
            return self.testrail_data.testplan_id

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
            print('[{}] Testrun updated with name "{}" and ID={}'.format(TESTRAIL_PREFIX,
                                                                         self.testrail_data.testrun_name,
                                                                         testrun_id))

    def update_testplan_entry(self, plan_id: int, entry_id: str, run_id: int, tr_keys: list, save_previous: bool = True):

        current_tests = []

        if save_previous:
            current_tests = get_case_list(self.get_tests(run_id=run_id))

        data = {
            'case_ids': list(set(tr_keys + current_tests)),
        }

        response = self.testrail_data.client.send_post(
            UPDATE_TESTPLAN_ENTRY.format(plan_id, entry_id),
            data,
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to update testrun: "{}"'.format(TESTRAIL_PREFIX, error))
        else:
            print('[{}] Testrun updated with name "{}" and ID={}, entry_id={}'.format(TESTRAIL_PREFIX,
                                                                                      self.testrail_data.testrun_name,
                                                                                      self.testrail_data.testrun_id,
                                                                                      entry_id))

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

    def get_cases(self, project_id, suit_id):
        """
       :return: the list of tests containing in a testrun.
       """
        response = self.testrail_data.client.send_get(
            GET_TESTCASES_URL.format(project_id, suit_id),
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to get tests: "{}"'.format(TESTRAIL_PREFIX, error))
            return None
        return response

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

    def get_plan(self, plan_id):
        """
        :return: a list of available testruns associated to a testplan in TestRail.

        """
        response = self.testrail_data.client.send_get(
            GET_TESTPLAN_URL.format(plan_id),
            cert_check=self.testrail_data.cert_check
        )
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to retrieve testplan: "{}"'.format(TESTRAIL_PREFIX, error))
        return response

    def get_testplan_entry_id(self, plan_id, run_id):
        """
        :return: a list of available testruns associated to a testplan in TestRail.

        """
        response = self.get_plan(plan_id)
        for entry in response['entries']:
            for run in entry['runs']:
                if str(run['id']) == run_id:
                    self.testrail_data.testplan_entry_id = entry['id']
                    return self.testrail_data.testplan_entry_id
        return None

    def get_available_testruns(self, plan_id):
        """
        :return: a list of available testruns associated to a testplan in TestRail.

        """
        testruns_list = []
        response = self.get_plan(plan_id)
        for entry in response['entries']:
            for run in entry['runs']:
                if not run['is_completed']:
                    testruns_list.append(run['id'])
        return testruns_list

    def is_testplan_available(self):
        """
        Ask if testplan is available in TestRail.

        :return: True if testplan exists AND is open
        """
        response = self.get_plan(self.testrail_data.testplan_id)
        error = self.testrail_data.client.get_error(response)
        if error:
            print('[{}] Failed to retrieve testplan: "{}"'.format(TESTRAIL_PREFIX, error))
            return False

        return response['is_completed'] is False