pytest-testrail
===============

[![Build Status](https://travis-ci.org/dubner/pytest-testrail.svg?branch=master)](https://travis-ci.org/dubner/pytest-testrail)


This is a pytest plugin for creating/editing testplans or testruns based on pytest markers.
The results of the collected tests will be updated against the testplan/testrun in TestRail.

Installation
------------

    pip install pytest-testrail


Configuration
-------------

Add a marker to the tests that will be picked up to be added to the run.

```python
from pytest_testrail.plugin import testrail

@testrail('C1234', 'C5678')
def test_foo():
    # test code goes here
```

See a [more detailed example here](tests/livetest/livetest.py).

Settings file template cfg:

```ini
[API]
url = https://yoururl.testrail.net/
email = user@email.com
password = <api_key>

[TESTRUN]
assignedto_id = 1
project_id = 1
suite_id = 1
```

Usage
-----

	py.test --testrail=<settings file>.cfg --tr_name='My Testrun Name'

This will creates a testrun in TestRail, add all marked tests to run.
Once the all tests are finished they will be updated in TestRail.

	py.test --testrail=<settings file>.cfg --run-id=1234

This will updates testrun in TestRail with ID 1234.

	py.test --testrail=<settings file>.cfg --plan-id=5678
	
This will updates testplan in TestRail with ID 5678.

### Options

	--tr_name='My Testrun Name'

Testruns can be named using the above flag, if this is not set a generated one will be used.
' Automation Run "timestamp" '

	--no-ssl-cert-check

This flag can be used prevent checking for a valid SSL certificate on TestRail host.

    --run-id=<id>
    
This option allows to precise an existing testrun  to update (by its TestRail ID). If provided, option `--tr_name` is ignored.

    --plan-id=<id>

This option allows to precise an existing test plan to update (by its TestRail ID). If provided, options `--tr_name` and
`--run-id` are ignored.
