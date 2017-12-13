# -*- coding: UTF-8 -*-
import pytest

from pytest_testrail.plugin import testrail, pytestrail

@testrail('C344', 'C366')
def test_func1():
    pass

@testrail('C345')
def test_func2():
    pytest.fail()

@testrail('C99999')
def test_func3():
    pass

@pytestrail.case('C1788')
def test_func4():
    pytest.skip()

@pytestrail.case('C1789')
def test_func5():
    pass
