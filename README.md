pytest-testrail
=================

[![Build Status](https://travis-ci.org/dubner/pytest-testrail.svg?branch=master)](https://travis-ci.org/dubner/pytest-testrail)


This is a pytest plugin for creating testruns based on pytest markers.
The results of the collected tests will also be updated against the testrun in TestRail.

Installation
------------

    pip install pytest-testrail


Configuration
-------------

Add a marker to the tests that will be picked up to be added to the run.

	from pytest_testrail.plugin import testrail

	@testrail('C1234', 'C5678')
	def test_foo():
		# test code goes here
	
    # OR	
	
	from pytest_testrail.plugin import pytestrail
	
	@pytestrail.case('C1234', 'C5678')
	def test_bar():
	    # test code goes here

Settings file template cfg:

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
	py.test --testrail=<settings file>.cfg

This will create a test run in TestRail, add all marked tests to run.
Once the all tests are finished they will be updated in TestRail.

	--tr-testrun-name='My Test Run'

Testruns can be named using the above flag, if this is not set a generated one will be used.
' Automation Run "timestamp" '

	--no-ssl-cert-check

This flag can be used prevent checking for a valid SSL certificate on TestRail host.

Available flags:

    --testrail [1,2]      
			  1.Create and update testruns with TestRail
			  2.Read testrun and update tests with TestRail
    --tr-url=TR_URL       TestRail address you use to access TestRail with your
                          web browser (config file: url in API section)
    --tr-email=TR_EMAIL   Email for the account on the TestRail server (config
                          file: email in API section)
    --tr-password=TR_PASSWORD
                          Password for the account on the TestRail server
                          (config file: password in API section) 
    --tr-no-ssl-cert-check
                          Do not check for valid SSL certificate on TestRail
                          host
	
   for testrail 1
    
    --tr-config=TR_CONFIG
                          Path to the config file containing information about
                          the TestRail server (defaults to testrail.cfg)
                          Path to the config file containing information about
                          the TestRail server (defaults to testrail.cfg)
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
                          host

   for testrail 2

    --tr-testrun-id=TR_TESTRUN_ID
                          ID of the test run containing the tests
    --tr-skip-passed-tests
                          Skip all passed tests in testrun
    --tr-skip-blocked-tests
                          Skip all blocked tests in testrun
    --tr-skip-untested-tests
                          Skip all untested tests in testrun
    --tr-skip-retest-tests
                          Skip all retest tests in testrun
    --tr-skip-failed-tests
                          Skip all failed tests in testrun

