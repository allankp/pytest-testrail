pytest-testrail
===============

|Build Status|

This is a pytest plugin for creating/editing testplans or testruns based
on pytest markers. The results of the collected tests will be updated
against the testplan/testrun in TestRail.

Installation
------------

::

    pip install pytest-testrail

Configuration
-------------

Config for Pytest tests
~~~~~~~~~~~~~~~~~~~~~~~

Add a marker to the tests that will be picked up to be added to the run.

.. code:: python

    from pytest_testrail.plugin import testrail

    @testrail('C1234', 'C5678')
    def test_foo():
        # test code goes here

    # OR    

    from pytest_testrail.plugin import pytestrail

    @pytestrail.case('C1234', 'C5678')
    def test_bar():
        # test code goes here

See a `more detailed example here <tests/livetest/livetest.py>`__.

Config for TestRail
~~~~~~~~~~~~~~~~~~~

-  Settings file template config:

.. code:: ini

    [API]
    url = https://yoururl.testrail.net/
    email = user@email.com
    password = <api_key>

    [TESTRUN]
    assignedto_id = 1
    project_id = 2
    suite_id = 3

Or

-  Set command line options (see below)

Usage
-----

Basically, the following command will create a testrun in TestRail, add
all marked tests to run. Once the all tests are finished they will be
updated in TestRail:

.. code:: bash

    py.test --testrail --tr-config=<settings file>.cfg

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
      --tr-testrun-assignedto-id=TR_TESTRUN_ASSIGNEDTO_ID
                            ID of the user assigned to the test run (config file:
                            assignedto_id in TESTRUN section)
      --tr-testrun-project-id=TR_TESTRUN_PROJECT_ID
                            ID of the project the test run is in (config file:
                            project_id in TESTRUN section)
      --tr-testrun-suite-id=TR_TESTRUN_SUITE_ID
                            ID of the test suite containing the test cases (config
                            file: suite_id in TESTRUN section)
      --tr-testrun-name=TR_TESTRUN_NAME
                            Name given to testrun, that appears in TestRail
                            (config file: name in TESTRUN section)
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

.. |Build Status| image:: https://travis-ci.org/dubner/pytest-testrail.svg?branch=master
   :target: https://travis-ci.org/dubner/pytest-testrail
