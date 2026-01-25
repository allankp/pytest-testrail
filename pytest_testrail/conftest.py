# -*- coding: UTF-8 -*-
"""
pytest-testrail configuration and plugin registration.

This module handles pytest options and TestRail plugin initialization.
"""
from __future__ import annotations

import configparser
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .plugin import PyTestRailPlugin
from .testrail_api import APIClient

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser

logger = logging.getLogger(__name__)


def pytest_addoption(parser: Parser) -> None:
    """Add pytest command line options for TestRail integration."""
    group = parser.getgroup("testrail")
    group.addoption(
        "--testrail",
        action="store_true",
        help="Create and update testruns with TestRail",
    )
    group.addoption(
        "--tr-config",
        action="store",
        default="testrail.cfg",
        help="Path to the config file containing information about the TestRail server (defaults to testrail.cfg)",
    )
    group.addoption(
        "--tr-url",
        action="store",
        help="TestRail address you use to access TestRail with your web browser (config file: url in API section)",
    )
    group.addoption(
        "--tr-email",
        action="store",
        help="Email for the account on the TestRail server (config file: email in API section)",
    )
    group.addoption(
        "--tr-password",
        action="store",
        help="Password for the account on the TestRail server (config file: password in API section)",
    )
    group.addoption(
        "--tr-api-key",
        action="store",
        help="API key for the account on the TestRail server. Preferred over password. (config file: api_key in API section)",
    )
    group.addoption(
        "--tr-timeout",
        action="store",
        type=float,
        help="Set timeout for connecting to TestRail server (config file: timeout in API section)",
    )
    group.addoption(
        "--tr-testrun-assignedto-id",
        action="store",
        help="ID of the user assigned to the test run (config file: assignedto_id in TESTRUN section)",
    )
    group.addoption(
        "--tr-testrun-project-id",
        action="store",
        help="ID of the project the test run is in (config file: project_id in TESTRUN section)",
    )
    group.addoption(
        "--tr-testrun-suite-id",
        action="store",
        help="ID of the test suite containing the test cases (config file: suite_id in TESTRUN section)",
    )
    group.addoption(
        "--tr-testrun-suite-include-all",
        action="store_true",
        default=None,
        help="Include all test cases in specified test suite when creating test run (config file: include_all in TESTRUN section)",
    )
    group.addoption(
        "--tr-testrun-name",
        action="store",
        default=None,
        help="Name given to testrun, that appears in TestRail (config file: name in TESTRUN section)",
    )
    group.addoption(
        "--tr-testrun-description",
        action="store",
        default=None,
        help="Description given to testrun, that appears in TestRail (config file: description in TESTRUN section)",
    )
    group.addoption(
        "--tr-run-id",
        action="store",
        default=0,
        required=False,
        help='Identifier of testrun, that appears in TestRail. If provided, option "--tr-testrun-name" will be ignored',
    )
    group.addoption(
        "--tr-plan-id",
        action="store",
        required=False,
        help='Identifier of testplan, that appears in TestRail (config file: plan_id in TESTRUN section). If provided, option "--tr-testrun-name" will be ignored',
    )
    group.addoption(
        "--tr-version",
        action="store",
        default="",
        required=False,
        help="Indicate a version in Test Case result",
    )
    group.addoption(
        "--tr-no-ssl-cert-check",
        action="store_false",
        default=None,
        help="Do not check for valid SSL certificate on TestRail host",
    )
    group.addoption(
        "--tr-close-on-complete",
        action="store_true",
        default=False,
        required=False,
        help="Close a test run on completion",
    )
    group.addoption(
        "--tr-dont-publish-blocked",
        action="store_false",
        required=False,
        help='Determine if results of "blocked" testcases (in TestRail) are published or not',
    )
    group.addoption(
        "--tr-skip-missing",
        action="store_true",
        required=False,
        help="Skip test cases that are not present in testrun",
    )
    group.addoption(
        "--tr-milestone-id",
        action="store",
        default=None,
        required=False,
        help="Identifier of milestone, to be used in run creation (config file: milestone_id in TESTRUN section)",
    )
    group.addoption(
        "--tc-custom-comment",
        action="store",
        default=None,
        required=False,
        help="Custom comment, to be appended to default comment for test case (config file: custom_comment in TESTCASE section)",
    )


def pytest_configure(config: Config) -> None:
    """Configure the TestRail plugin if enabled."""
    if config.getoption("--testrail"):
        cfg_file_path = config.getoption("--tr-config")
        config_manager = ConfigManager(cfg_file_path, config)

        # Get authentication credentials (prefer API key over password)
        api_key = config_manager.getoption("tr-api-key", "api_key", "API")
        password = config_manager.getoption("tr-password", "password", "API")
        auth_credential_val = api_key or password
        auth_credential = str(auth_credential_val) if auth_credential_val and auth_credential_val is not True else ""

        if not auth_credential:
            logger.warning(
                "No TestRail password or API key provided. "
                "Use --tr-api-key or --tr-password, or set in config file."
            )

        # Get timeout with proper type conversion
        timeout_value = config_manager.getoption("tr-timeout", "timeout", "API")
        timeout = None
        if timeout_value:
            try:
                timeout = float(timeout_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid TestRail API timeout value '{timeout_value}'. "
                    "Please provide a numeric value (seconds) for 'tr-timeout'/'timeout'."
                ) from exc

        # Get string values for APIClient (with proper type handling)
        url = config_manager.getoption("tr-url", "url", "API")
        email = config_manager.getoption("tr-email", "email", "API")

        client = APIClient(
            str(url) if url else "",
            str(email) if email else "",
            auth_credential or "",
            timeout=timeout,
        )

        # Get boolean values with explicit type handling
        include_all_val = config_manager.getoption(
            "tr-testrun-suite-include-all", "include_all", "TESTRUN", is_bool=True, default=False
        )
        include_all = bool(include_all_val) if include_all_val is not None else False

        cert_check_val = config_manager.getoption(
            "tr-no-ssl-cert-check", "no_ssl_cert_check", "API", is_bool=True, default=True
        )
        cert_check = bool(cert_check_val) if cert_check_val is not None else True

        # Get string values with explicit type handling
        tr_name_val = config_manager.getoption("tr-testrun-name", "name", "TESTRUN")
        tr_name = str(tr_name_val) if tr_name_val and tr_name_val is not True else None

        tr_description_val = config_manager.getoption("tr-testrun-description", "description", "TESTRUN")
        tr_description = str(tr_description_val) if tr_description_val and tr_description_val is not True else ""

        custom_comment_val = config_manager.getoption("tc-custom-comment", "custom_comment", "TESTCASE")
        custom_comment = str(custom_comment_val) if custom_comment_val and custom_comment_val is not True else None

        config.pluginmanager.register(
            PyTestRailPlugin(
                client=client,
                assign_user_id=config_manager.getoption("tr-testrun-assignedto-id", "assignedto_id", "TESTRUN"),
                project_id=config_manager.getoption("tr-testrun-project-id", "project_id", "TESTRUN") or 0,
                suite_id=config_manager.getoption("tr-testrun-suite-id", "suite_id", "TESTRUN") or 0,
                include_all=include_all,
                cert_check=cert_check,
                tr_name=tr_name,
                tr_description=tr_description,
                run_id=config.getoption("--tr-run-id"),
                plan_id=config_manager.getoption("tr-plan-id", "plan_id", "TESTRUN") or 0,
                version=config.getoption("--tr-version"),
                close_on_complete=config.getoption("--tr-close-on-complete"),
                publish_blocked=config.getoption("--tr-dont-publish-blocked"),
                skip_missing=config.getoption("--tr-skip-missing"),
                milestone_id=config_manager.getoption("tr-milestone-id", "milestone_id", "TESTRUN"),
                custom_comment=custom_comment,
            ),
            # Name of plugin instance (allow to be used by other plugins)
            name="pytest-testrail-instance",
        )


class ConfigManager:
    """
    Handle configuration from CLI options and config file.

    CLI options take precedence over config file values.
    """

    def __init__(self, cfg_file_path: str, config: Config) -> None:
        """
        Initialize the config manager.

        Args:
            cfg_file_path: Path to the config file.
            config: pytest config object with CLI options.
        """
        self.cfg_file: configparser.ConfigParser | None = None
        cfg_path = Path(cfg_file_path)

        if cfg_path.is_file() or cfg_path.is_symlink():
            self.cfg_file = configparser.ConfigParser()
            self.cfg_file.read(cfg_file_path)

        self.config = config

    def getoption(
        self,
        flag: str,
        cfg_name: str,
        section: str | None = None,
        *,
        is_bool: bool = False,
        default: str | bool | None = None,
    ) -> str | bool | None:
        """
        Get a configuration option.

        Priority order:
        1. CLI option
        2. Config file value
        3. Default value

        Args:
            flag: CLI flag name (without --).
            cfg_name: Config file option name.
            section: Config file section name.
            is_bool: Whether the option is a boolean.
            default: Default value if not found.

        Returns:
            The configuration value.
        """
        # 1. Return CLI option (if set)
        value = self.config.getoption(f"--{flag}")
        if value is not None:
            return value  # type: ignore[no-any-return]

        # 2. Return default if no config file path is specified
        if section is None or self.cfg_file is None:
            return default

        if self.cfg_file.has_option(section, cfg_name):
            # 3. Return config file value
            if is_bool:
                return self.cfg_file.getboolean(section, cfg_name)
            return self.cfg_file.get(section, cfg_name)  # type: ignore[no-any-return]

        # 4. If entry not found in config file
        return default
