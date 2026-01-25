# -*- coding: UTF-8 -*-
import os.path
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))

from pytest_testrail.conftest import pytest_addoption, pytest_configure  # noqa: F401, E402
