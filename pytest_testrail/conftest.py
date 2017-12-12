import os
import sys
if sys.version_info.major == 2:
    # python2
    import ConfigParser as configparser
else:
    # python3
    import configparser

from .plugin import PyTestRailPlugin, PyTestRailPlugin2
from .testrail_api import APIClient


def pytest_addoption(parser):
    group = parser.getgroup('testrail')
    group.addoption(
        '--testrail',
        choices=['1', '2'],
        action='store',
        help='''1.Create and update tests in testruns with TestRail\n 
                2.Read testrun and update tests with TestRail''')
    group.addoption(
        '--tr-url',
        action='store',
        help='TestRail address you use to access TestRail with your web browser (config file: url in API section)')
    group.addoption(
        '--tr-email',
        action='store',
        help='Email for the account on the TestRail server (config file: email in API section)')
    group.addoption(
        '--tr-password',
        action='store',
        help='Password for the account on the TestRail server (config file: password in API section)')
    group.addoption(
        '--tr-no-ssl-cert-check',
        action='store_false',
        default=True,
        help='Do not check for valid SSL certificate on TestRail host')

    group_create_testrun = parser.getgroup('testrail create test run')
    group_create_testrun.addoption(
        '--tr-config',
        action='store',
        default='testrail.cfg',
        help='Path to the config file containing information about the TestRail server (defaults to testrail.cfg)')
    group_create_testrun.addoption(
        '--tr-testrun-assignedto-id',
        action='store',
        help='ID of the user assigned to the test run (config file: assignedto_id in TESTRUN section)')
    group_create_testrun.addoption(
        '--tr-testrun-project-id',
        action='store',
        help='ID of the project the test run is in (config file: project_id in TESTRUN section)')
    group_create_testrun.addoption(
        '--tr-testrun-suite-id',
        action='store',
        help='ID of the test suite containing the test cases (config file: suite_id in TESTRUN section)')
    group_create_testrun.addoption(
        '--tr-testrun-name',
        action='store',
        default=None,
        help='Name given to testrun, that appears in TestRail (config file: name in TESTRUN section)')


    group_exist_testrun = parser.getgroup('testrail use exist test run')
    group_exist_testrun.addoption(
        '--tr-testrun-id',
        action='store',
        default=None,
        help='ID of the test run containing the tests',)
    group_exist_testrun.addoption(
        '--tr-skip-passed-tests',
        action='store_true',
        default=False,
        help='Skip all passed tests in testrun', )
    group_exist_testrun.addoption(
        '--tr-skip-blocked-tests',
        action='store_true',
        default=False,
        help='Skip all blocked tests in testrun', )
    group_exist_testrun.addoption(
        '--tr-skip-untested-tests',
        action='store_true',
        default=False,
        help='Skip all untested tests in testrun', )
    group_exist_testrun.addoption(
        '--tr-skip-retest-tests',
        action='store_true',
        default=False,
        help='Skip all retest tests in testrun', )
    group_exist_testrun.addoption(
        '--tr-skip-failed-tests',
        action='store_true',
        default=False,
        help='Skip all failed tests in testrun', )

def pytest_configure(config):
    if config.getoption('--testrail') == "1":
        cfg_file_path = config.getoption('--tr-config')
        config_manager = ConfigManager(cfg_file_path, config)
        client = APIClient(config_manager.getoption('tr-url', 'url', 'API'),
                           config_manager.getoption('tr-email', 'email', 'API'),
                           config_manager.getoption('tr-password', 'password', 'API'))

        config.pluginmanager.register(
            PyTestRailPlugin(
                client=client,
                assign_user_id=config_manager.getoption('tr-testrun-assignedto-id', 'assignedto_id', 'TESTRUN'),
                project_id=config_manager.getoption('tr-testrun-project-id', 'project_id', 'TESTRUN'),
                suite_id=config_manager.getoption('tr-testrun-suite-id', 'suite_id', 'TESTRUN'),
                cert_check=config_manager.getoption('tr-no-ssl-cert-check', 'no_ssl_cert_check', 'API', default=True),
                tr_name=config_manager.getoption('tr-testrun-name', 'name', 'TESTRUN')
            )
        )
    elif config.getoption('--testrail') == "2":

        client = APIClient(config.getoption("--tr-url"),
                           config.getoption("--tr-email"),
                           config.getoption("--tr-password"))
        testrun_id = config.getoption("--tr-testrun-id")

        assert testrun_id

        type_skip_list = list()
        if config.getoption("--tr-skip-passed-tests"):
            type_skip_list.append(1)
        if config.getoption("--tr-skip-blocked-tests"):
            type_skip_list.append(2)
        if config.getoption("--tr-skip-untested-tests"):
            type_skip_list.append(3)
        if config.getoption("--tr-skip-retest-tests"):
            type_skip_list.append(4)
        if config.getoption("--tr-skip-failed-tests"):
            type_skip_list.append(5)

        ssl_cert_check = config.getoption('--tr-no-ssl-cert-check')

        config.pluginmanager.register(
            PyTestRailPlugin2(client, testrun_id, ssl_cert_check, type_skip_list)
        )


class ConfigManager(object):
    def __init__(self, cfg_file_path, config):
        '''
        Handles retrieving configuration values. Config options set in flags are given preferance over options set in the
        config file.

        :param cfg_file_path: Path to the config file containing information about the TestRail server.
        :type cfg_file_path: str or None
        :param config: Config object containing commandline flag options.
        :type config: _pytest.config.Config
        '''
        self.cfg_file = None
        if os.path.isfile(cfg_file_path) or os.path.islink(cfg_file_path):
            self.cfg_file = configparser.ConfigParser()
            self.cfg_file.read(cfg_file_path)

        self.config = config

    def getoption(self, flag, cfg_name, section=None, default=None):
        value = self.config.getoption('--{}'.format(flag))
        if value is not None:
            return value
        if section is None or self.cfg_file is None:
            return None
        return self.cfg_file.get(section, cfg_name, fallback=None)
