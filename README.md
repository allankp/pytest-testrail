pytest-testrail
===============

[![Build Status](https://travis-ci.org/allankp/pytest-testrail.svg?branch=master)](https://travis-ci.org/allankp/pytest-testrail)
[![PyPI version](https://badge.fury.io/py/pytest-testrail.svg)](https://badge.fury.io/py/pytest-testrail)
[![Downloads](https://pepy.tech/badge/pytest-testrail)](https://pepy.tech/project/pytest-testrail)


This is a pytest plugin for creating/editing testplans or testruns based on pytest markers.
The results of the collected tests will be updated against the testplan/testrun in TestRail.

Installation
------------

    pip install pytest-testrail


Configuration
-------------

### Config for Pytest tests

Add a marker to the tests that will be picked up to be added to the run.

```python
from pytest_testrail.plugin import testrail

@testrail('C1234', 'C5678')
def test_foo():
    # test code goes here

# OR	

from pytest_testrail.plugin import pytestrail

@pytestrail.case('C1234', 'C5678')
def test_bar():
    # test code goes here
```

Or if you want to add defects to testcase result:

```python

from pytest_testrail.plugin import pytestrail

@pytestrail.defect('PF-524', 'BR-543')
def test_bar():
    # test code goes here
```

### Config for TestRail

* Settings file template config:

```ini
[API]
url = https://yoururl.testrail.net/
email = user@email.com
password = <api_key>

[TESTRUN]
assignedto_id = 1
project_id = 2
suite_id = 3
plan_id = 4
description = 'This is an example description'
```

Or

* Set command line options (see below)

Usage
-----

Basically, the following command will create a testrun in TestRail, add all marked tests to run.
Once the all tests are finished they will be updated in TestRail:

```bash
py.test --testrail --tr-config=<settings file>.cfg
```

### All available options

| option                         | description                                                                                                         |
| -------------------------------|---------------------------------------------------------------------------------------------------------------------|
| --testrail                     | Create and update testruns with TestRail                                                                            |
| --tr-config                    | Path to the config file containing information about the TestRail server (defaults to testrail.cfg)                 |
| --tr-url                       | TestRail address you use to access TestRail with your web browser (config file: url in API section)                 |
| --tr-email                     | Email for the account on the TestRail server (config file: email in API section)                                    |
| --tr-password                  | Password for the account on the TestRail server (config file: password in API section)                              |
| --tr-testrun-assignedto-id     | ID of the user assigned to the test run (config file:assignedto_id in TESTRUN section)                              |
| --tr-testrun-project-id        | ID of the project the test run is in (config file: project_id in TESTRUN section)                                   |
| --tr-testrun-suite-id          | ID of the test suite containing the test cases (config file: suite_id in TESTRUN section)                           |
| --tr-testrun-suite-include-all | Include all test cases in specified test suite when creating test run (config file: include_all in TESTRUN section) |
| --tr-testrun-name              | Name given to testrun, that appears in TestRail (config file: name in TESTRUN section)                              |
| --tr-testrun-description       | Description given to testrun, that appears in TestRail (config file: description in TESTRUN section)                |
| --tr-run-id                    | Identifier of testrun, that appears in TestRail. If provided, option "--tr-testrun-name" will be ignored            |
| --tr-plan-id                   | Identifier of testplan, that appears in TestRail. If provided, option "--tr-testrun-name" will be ignored           |
| --tr-version                   | Indicate a version in Test Case result.                                                                             |
| --tr-no-ssl-cert-check         | Do not check for valid SSL certificate on TestRail host                                                             |
| --tr-close-on-complete         | Close a test plan or test run on completion.                                                                        |
| --tr-dont-publish-blocked      | Do not publish results of "blocked" testcases in TestRail                                                           |
| --tr-skip-missing              | Skip test cases that are not present in testrun                                                                     |
|  --tr-milestone-id             | Identifier of milestone to be assigned to run                                                                       |