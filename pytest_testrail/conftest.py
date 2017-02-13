import configparser

from .plugin import TestRailPlugin
from .testrail_api import APIClient


def pytest_addoption(parser):
    group = parser.getgroup('testrail')
    group.addoption(
        '--testrail',
        action='store',
        help='Create and update testruns with TestRail')
    group.addoption(
        '--no-ssl-cert-check',
        action='store_true',
        default=False,
        required=False,
        help='Do not check for valid SSL certificate on TestRail host'
    )
    group.addoption(
        '--tr_name',
        action='store',
        default=None,
        required=False,
        help='Name given to testrun, that appears in TestRail'
    )
    group.addoption(
        '--update-existing-run',
        action='store_true',
        default=False,
        required=False,
        help='Updates an existing run if one is found'
    )


def pytest_configure(config):
    if config.option.testrail:
        cfg_file = read_config_file(config.getoption("--testrail"))
        client = APIClient(cfg_file.get('API', 'url'))
        client.user = cfg_file.get('API', 'email')
        client.password = cfg_file.get('API', 'password', raw=True)
        ssl_cert_check = True
        tr_name = config.getoption('--tr_name')
        update_existing = False

        if config.getoption('--no-ssl-cert-check') is True:
            ssl_cert_check = False
        if config.getoption('--update-existing-run') is True:
            update_existing = True

        config.pluginmanager.register(
            TestRailPlugin(
                client=client,
                assign_user_id=cfg_file.get('TESTRUN', 'assignedto_id'),
                project_id=cfg_file.get('TESTRUN', 'project_id'),
                suite_id=cfg_file.get('TESTRUN', 'suite_id'),
                cert_check=ssl_cert_check,
                tr_name=tr_name,
                update=update_existing
            )
        )


def read_config_file(configfile):
    config = configparser.ConfigParser()
    config.read(configfile)
    return config
