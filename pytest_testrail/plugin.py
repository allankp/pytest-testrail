# -*- coding: UTF-8 -*-
import pytest

from pytest_testrail.TestrailModel import TestRailModel
from pytest_testrail.testrail_actions import TestrailActions
from pytest_testrail.vars import TESTRAIL_DEFECTS_PREFIX, TESTRAIL_PREFIX
from pytest_testrail.functions import get_testrail_keys, testrun_name, clean_test_ids, \
    get_test_outcome, clean_test_defects, is_xdist_worker, get_testrail_suite_ids, get_suite_by_case


class PyTestRailPlugin(TestrailActions):

    def __init__(self, client, assign_user_id, project_id, suite_id, include_all, cert_check, tr_name,
                 tr_description='', testplan_name=None, testplan_description=None, run_id=0, plan_id=0, version='',
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
                                           testplan_name=testplan_name,
                                           testplan_description=testplan_description,
                                           version=version,
                                           close_on_complete=close_on_complete,
                                           publish_blocked=publish_blocked,
                                           skip_missing=skip_missing,
                                           milestone_id=milestone_id,
                                           custom_comment=custom_comment,
                                           tr_keys=[],
                                           user_email=user_email,
                                           user_password=user_password,
                                           tr_url=tr_url,
                                           actual_suites_with_case_ids={},
                                           plan_entry_storage={},
                                           diff_case_ids=[]
                                           )
        super().__init__(testrail_data=self.testrail_data)
        self.is_use_xdist = False

    def _create_test_plan(self):
        self.create_plan(self.testrail_data.project_id,
                         self.testrail_data.testplan_name,
                         self.testrail_data.milestone_id,
                         self.testrail_data.testplan_description)

    def _create_test_plan_entry(self, suite_id=None, test_suite_name=''):
        self.create_plan_entry(suite_id=suite_id if suite_id else self.testrail_data.suite_id,
                               testrun_name=f'[ {test_suite_name} ] {self.testrail_data.testrun_name or testrun_name()}',
                               assign_user_id=self.testrail_data.assign_user_id,
                               plan_id=self.testrail_data.testplan_id,
                               include_all=self.testrail_data.include_all,
                               tr_keys=self.testrail_data.actual_suites_with_case_ids[
                                   suite_id if suite_id else self.testrail_data.suite_id],
                               description=self.testrail_data.testrun_description
                               )

    def _create_test_run(self, suite_id=None, test_suite_name=''):
        self.create_test_run(assign_user_id=self.testrail_data.assign_user_id,
                             project_id=self.testrail_data.project_id,
                             suite_id=suite_id if suite_id else self.testrail_data.suite_id,
                             include_all=self.testrail_data.include_all,
                             testrun_name=f'[ {test_suite_name} ] {self.testrail_data.testrun_name or testrun_name()}',
                             tr_keys=self.testrail_data.actual_suites_with_case_ids[
                                 suite_id if suite_id else self.testrail_data.suite_id],
                             milestone_id=self.testrail_data.milestone_id,
                             description=self.testrail_data.testrun_description
                             )

    # pytest hooks
    def pytest_report_header(self, config, startdir):
        """ Add extra-info in header """
        message = f'[{TESTRAIL_PREFIX}]: '
        if self.testrail_data.testplan_id:
            message += 'existing testplan #{} selected'.format(self.testrail_data.testplan_id)
        elif self.testrail_data.testrun_id:
            message += 'existing testrun #{} selected'.format(self.testrail_data.testrun_id)
        else:
            message += 'a new testrun will be created'
        return message

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        # получили все тесты с тест-номерами из прогона
        items_with_tr_keys = get_testrail_keys(items)

        # ---------------------------------------------
        testrail_list_of_suites_and_cases = {}
        available_suite_ids = self.get_suites(project_id=self.testrail_data.project_id)
        available_suite_ids = {suite['id']: suite['name'] for suite in available_suite_ids}
        # получили список тест-сьютов [11234,34234,123213]
        if self.testrail_data.suite_id:
            suite_ids = {int(self.testrail_data.suite_id)}
        else:
            # получили все тесты с тест-сьютами из прогона
            items_with_suite_ids = get_testrail_suite_ids(items)
            suite_ids = {suite for item in items_with_suite_ids for suite in item[1]}

            for suite_id in suite_ids:
                if suite_id not in available_suite_ids.keys():
                    print(f"[{TESTRAIL_PREFIX}] Test suite ({suite_id}) not available "
                          f"for project_id: {self.testrail_data.project_id}")

        # получили список тест-сьютов с соответствующими тест-кейсами из тестрейла
        for suite_id in suite_ids:
            testrail_list_of_suites_and_cases[suite_id] = \
                [test.get('id') for test in self.get_cases(self.testrail_data.project_id, suite_id)]

        # ---------------------------------------------
        # получили список всех тест-номеров в прогоне
        pytest_case_ids = [case_id for item in items_with_tr_keys for case_id in item[1]]

        # получили список всех тест-кейсов со всех тест-сьютов
        suite_case_ids = [case for value in testrail_list_of_suites_and_cases for case in
                          testrail_list_of_suites_and_cases[value]]

        # получили список тест-кейсов которые нужно запустить
        self.testrail_data.tr_keys = [case for case in pytest_case_ids if case in suite_case_ids]

        # получили список тест-сьютов с участвующими тест-кейсами в прогоне
        for suite_id in suite_ids:
            self.testrail_data.actual_suites_with_case_ids[suite_id] = list(
                set(pytest_case_ids).intersection(testrail_list_of_suites_and_cases[suite_id]))
        print(f"[{TESTRAIL_PREFIX}] PyTest cases: {pytest_case_ids}")
        # получили список тест-кейсов, которых нет в прогоне
        self.testrail_data.diff_case_ids = list(set(pytest_case_ids).difference(suite_case_ids))

        # вывели список тест-кейсов которых нет в тест-сьютах
        if self.testrail_data.diff_case_ids:
            print(f"[{TESTRAIL_PREFIX}] In pytest run have testcases that not exist in suites\n"
                  f"[{TESTRAIL_PREFIX}] Diff: {self.testrail_data.diff_case_ids}")

        if self.testrail_data.testrun_id:
            # update specified test run
            run_info = self.get_run(run_id=self.testrail_data.testrun_id)
            if run_info['plan_id']:
                entry_id = self.get_testplan_entry_id(plan_id=run_info['plan_id'],
                                                      run_id=self.testrail_data.testrun_id
                                                      )
                self.update_testplan_entry(plan_id=run_info['plan_id'], entry_id=entry_id,
                                           run_id=self.testrail_data.testrun_id,
                                           tr_keys=self.testrail_data.actual_suites_with_case_ids[run_info['suite_id']],
                                           suite_id=run_info['suite_id'],
                                           save_previous=True)
            else:
                self.update_testrun(testrun_id=self.testrail_data.testrun_id,
                                    tr_keys=self.testrail_data.actual_suites_with_case_ids[run_info['suite_id']],
                                    suite_id=run_info['suite_id'],
                                    save_previous=True)
        else:
            # create testrun for each suite
            for suite_id in self.testrail_data.actual_suites_with_case_ids.keys():
                if not self.testrail_data.actual_suites_with_case_ids[suite_id]:
                    print(f"[{TESTRAIL_PREFIX}] No testcases for suite {suite_id}! Testrun not created")
                    continue
                if self.testrail_data.testplan_id:
                    self._create_test_plan_entry(suite_id=suite_id, test_suite_name=available_suite_ids.get(suite_id))
                else:
                    self._create_test_run(suite_id=suite_id, test_suite_name=available_suite_ids.get(suite_id))
        if self.testrail_data.skip_missing:
            for item, case_id in items_with_tr_keys:
                if set(case_id).intersection(set(self.testrail_data.diff_case_ids)):
                    mark = pytest.mark.skip(f'[{TESTRAIL_PREFIX}] Test {case_id} is not present in testrun.')
                    item.add_marker(mark)

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
                    suite_id = get_suite_by_case(case=testcase_id,
                                                 suites=self.testrail_data.actual_suites_with_case_ids)

                    self.testrail_data.results.append(self.add_result(
                        testcase_id,
                        get_test_outcome(outcome.get_result().outcome),
                        comment=comment,
                        duration=rep.duration,
                        defects=str(clean_test_defects(defect_ids)).replace('[', '').replace(']', '').replace("'",
                                                                                                              '') if defect_ids else None,
                        test_parametrize=test_parametrize,
                        suite_id=suite_id))
            return None

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        if is_xdist_worker(config=session.config):
            self.testrail_data.testrun_id = session.config.workerinput["test_run_id"]
        else:
            if not self.testrail_data.testrun_id and not self.testrail_data.testplan_id \
                    and self.testrail_data.testplan_name:
                self._create_test_plan()

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
