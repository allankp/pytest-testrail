pytest-testrail
===============

|Build Status|

This is a pytest plugin for creating testruns based on pytest markers.
The results of the collected tests will also be updated against the
testrun in TestRail.

Installation
------------

::

    pip install pytest-testrail

Configuration
-------------

Add a marker to the tests that will be picked up to be added to the run.

::

    from pytest_testrail.plugin import testrail

    @testrail('C1234', 'C5678')
    def test_foo():
        # test code goes here

Settings file template cfg:

::

    [API]
    url = https://yoururl.testrail.net/
    email = user@email.com
    password = password

    [TESTRUN]
    assignedto_id = 1
    project_id = 1
    suite_id = 1

Usage
-----

::

    py.test --testrail=<settings file>.cfg

This will create a test run in TestRail, add all marked tests to run.
Once the all tests are finished they will be updated in TestRail.

.. |Build Status| image:: https://travis-ci.org/allankilpatrick/pytest-testrail.svg?branch=master
   :target: https://travis-ci.org/allankilpatrick/pytest-testrail
