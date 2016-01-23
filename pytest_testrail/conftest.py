import configparser

from plugin import TestRailPlugin
from testrail_api import APIClient


def pytest_addoption(parser):
    group = parser.getgroup('testrail')
    group.addoption(
        '--testrail',
        action='store',
        help='Create and update testruns with TestRail')


def pytest_configure(config):
    if config.option.testrail:
        cfg_file = read_config_file(config.getoption("--testrail"))
        client = APIClient(cfg_file.get('API', 'url'))
        client.user = cfg_file.get('API', 'email')
        client.password = cfg_file.get('API', 'password')

        config.pluginmanager.register(
            TestRailPlugin(
                client,
                cfg_file.get('TESTRUN', 'assignedto_id'),
                cfg_file.get('TESTRUN', 'project_id'),
                cfg_file.get('TESTRUN', 'suite_id')
            )
        )


def read_config_file(configfile):
    config = configparser.ConfigParser()
    config.read(configfile)
    return config
