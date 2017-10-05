#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import pytest
import time

from pytest_testrail.plugin import testrail

@testrail('C344', 'C366')
def test_func1():
    time.sleep(0.5)

@testrail('C345')
def test_func2():
    time.sleep(1.6)
    pytest.fail()

@testrail('C99999')
def test_func3():
    time.sleep(0.5)

@testrail('C1788')
def test_func4():
    pytest.skip()

@testrail('C1789')
def test_func5():
    time.sleep(0.5)
