pytest-testrail
===============

|PyPI version| |Python versions|

This is a pytest plugin for creating/editing testplans or testruns based
on pytest markers. The results of the collected tests will be updated
against the testplan/testrun in TestRail.

**Version 3.0** brings major modernization:

- Python 3.10+ required (Python 2 support dropped)
- Full type hints throughout the codebase
- Support for TestRail API pagination (TestRail 6.7+)
- Proper exception handling with custom exception classes
- API key authentication support (recommended over password)
- Connection pooling via requests Session
- Automatic retry on rate limiting (HTTP 429)
- Logging instead of print statements

Installation
------------

Using uv (recommended):

::

   uv add pytest-testrail

Or using pip:

::

   pip install pytest-testrail

Configuration
-------------

Config for Pytest tests
~~~~~~~~~~~~~~~~~~~~~~~

Add a marker to the tests that will be picked up to be added to the run.

.. code:: python

   from pytest_testrail.plugin import pytestrail

   @pytestrail.case('C1234', 'C5678')
   def test_foo():
       # test code goes here

   # With defect tracking
   @pytestrail.case('C1234')
   @pytestrail.defect('BUG-123', 'JIRA-456')
   def test_bar():
       # test code goes here

.. note::
   The ``@testrail`` decorator is deprecated. Please use ``@pytestrail.case`` instead.

See a `more detailed example here <tests/livetest/livetest.py>`__.

Config for TestRail
~~~~~~~~~~~~~~~~~~~

-  Settings file template config:

.. code:: ini

   [API]
   url = https://yoururl.testrail.net/
   email = user@email.com
   # Use API key (recommended) or password
   api_key = your-api-key
   # password = your-password
   # timeout = 30

   [TESTRUN]
   assignedto_id = 1
   project_id = 2
   suite_id = 3
   # Optional settings
   # plan_id = 100
   # milestone_id = 1
   # include_all = false

   [TESTCASE]
   # custom_comment = Additional info appended to results

Or

-  Set command line options (see below)

Usage
-----

Basically, the following command will create a testrun in TestRail, add
all marked tests to run. Once the all tests are finished they will be
updated in TestRail:

.. code:: bash

   pytest --testrail --tr-config=<settings file>.cfg

Using API Key (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

API keys are more secure than passwords and can be revoked without
changing your password. Generate an API key in TestRail under
*My Settings*.

.. code:: bash

   pytest --testrail --tr-url=https://example.testrail.net --tr-email=user@example.com --tr-api-key=your-api-key --tr-testrun-project-id=1 --tr-testrun-suite-id=1

All available options
~~~~~~~~~~~~~~~~~~~~~

::

     --testrail            Create and update testruns with TestRail
     --tr-config=TR_CONFIG
                           Path to the config file containing information about
                           the TestRail server (defaults to testrail.cfg)
     --tr-url=TR_URL       TestRail address you use to access TestRail with your
                           web browser (config file: url in API section)
     --tr-email=TR_EMAIL   Email for the account on the TestRail server (config
                           file: email in API section)
     --tr-password=TR_PASSWORD
                           Password for the account on the TestRail server
                           (config file: password in API section)
     --tr-api-key=TR_API_KEY
                           API key for the account on the TestRail server
                           (recommended over password)
                           (config file: api_key in API section)
     --tr-timeout=TR_TIMEOUT
                           Set timeout for connecting to TestRail server
                           (config file: timeout in API section)
     --tr-testrun-assignedto-id=TR_TESTRUN_ASSIGNEDTO_ID
                           ID of the user assigned to the test run (config file:
                           assignedto_id in TESTRUN section)
     --tr-testrun-project-id=TR_TESTRUN_PROJECT_ID
                           ID of the project the test run is in (config file:
                           project_id in TESTRUN section)
     --tr-testrun-suite-id=TR_TESTRUN_SUITE_ID
                           ID of the test suite containing the test cases (config
                           file: suite_id in TESTRUN section)
     --tr-testrun-suite-include-all
                           Include all test cases in specified test suite when
                           creating test run (config file: include_all in TESTRUN
                           section)
     --tr-testrun-name=TR_TESTRUN_NAME
                           Name given to testrun, that appears in TestRail
                           (config file: name in TESTRUN section)
     --tr-testrun-description=TR_TESTRUN_DESCRIPTION
                           Description given to testrun, that appears in TestRail
                           (config file: description in TESTRUN section)
     --tr-run-id=TR_RUN_ID
                           Identifier of testrun, that appears in TestRail. If
                           provided, option "--tr-testrun-name" will be ignored
     --tr-plan-id=TR_PLAN_ID
                           Identifier of testplan, that appears in TestRail. If
                           provided, option "--tr-testrun-name" will be ignored
     --tr-version=TR_VERSION
                           Indicate a version in Test Case result.
     --tr-no-ssl-cert-check
                           Do not check for valid SSL certificate on TestRail
                           host
     --tr-close-on-complete
                           Close a test plan or test run on completion.
     --tr-dont-publish-blocked
                           Do not publish results of "blocked" testcases in
                           TestRail
     --tr-skip-missing     Skip test cases that are not present in testrun
     --tr-milestone-id=TR_MILESTONE_ID
                           Identifier of milestone, to be used in run creation
                           (config file: milestone_id in TESTRUN section)
     --tc-custom-comment=TC_CUSTOM_COMMENT
                           Custom comment, to be appended to default comment for
                           test case (config file: custom_comment in TESTCASE
                           section)

Programmatic Usage
------------------

You can also use the API client directly in your code:

.. code:: python

   from pytest_testrail import APIClient, TestRailError

   # Create client
   client = APIClient(
       base_url="https://example.testrail.net",
       user="user@example.com",
       password="your-api-key"  # Can be API key or password
   )

   # Use context manager for automatic cleanup
   with client:
       # Get a test case
       case = client.send_get("get_case/1")

       # Add a result
       result = client.send_post("add_result/1", {
           "status_id": 1,
           "comment": "Test passed!"
       })

       # Handle paginated results
       for test in client.get_paginated("get_tests/1", "tests"):
           print(test["case_id"])

Exception Handling
~~~~~~~~~~~~~~~~~~

.. code:: python

   from pytest_testrail import (
       APIClient,
       TestRailError,
       TestRailAPIError,
       TestRailAuthenticationError,
       TestRailRateLimitError
   )

   try:
       client = APIClient(base_url, user, api_key)
       result = client.send_get("get_case/1")
   except TestRailAuthenticationError:
       print("Invalid credentials")
   except TestRailRateLimitError:
       print("Rate limit exceeded")
   except TestRailAPIError as e:
       print(f"API error: {e.message}")
   except TestRailError as e:
       print(f"General error: {e}")

Development
-----------

This project uses `uv <https://docs.astral.sh/uv/>`__ for dependency management.

.. code:: bash

   # Clone and install
   git clone https://github.com/allankp/pytest-testrail.git
   cd pytest-testrail
   uv sync

   # Run tests
   uv run pytest

   # Run linting
   uv run ruff check pytest_testrail tests
   uv run mypy pytest_testrail

   # Test with different Python versions
   uv run --python 3.10 pytest
   uv run --python 3.12 pytest

Changelog
---------

See `CHANGELOG.md <CHANGELOG.md>`__ for version history.

.. |Build Status| image:: https://github.com/allankp/pytest-testrail/workflows/Tests/badge.svg
   :target: https://github.com/allankp/pytest-testrail/actions
.. |PyPI version| image:: https://badge.fury.io/py/pytest-testrail.svg
   :target: https://badge.fury.io/py/pytest-testrail
.. |Python versions| image:: https://img.shields.io/pypi/pyversions/pytest-testrail.svg
   :target: https://pypi.org/project/pytest-testrail/

