from setuptools import setup
import sys

long_description = "pytest plugin for TestRail"
try:
    long_description = open("README.rst").read()
except Exception as e:
    print '{} {}'.format(e, file=sys.stderr)

setup(
    name='pytest-testrail',
    description='pytest plugin for creating TestRail runs and adding results',
    long_description=long_description,
    version='0.0.6',
    author='Allan Kilpatrick',
    author_email='allanklp@gmail.com',
    url='http://github.com/allankilpatrick/pytest-testrail/',
    packages=[
        'pytest_testrail',
    ],
    package_dir={'pytest_testrail': 'pytest_testrail'},
    install_requires=[
        'pytest>=2,<3',
        'configparser>=3,<4',
        'requests==2.11.1'
    ],
    include_package_data=True,
    entry_points={'pytest11': ['pytest-testrail = pytest_testrail.conftest']},
)
