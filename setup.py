from setuptools import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='pytest-testrail',
    description='pytest plugin for creating TestRail runs and adding results',
    long_description=long_description,
    version='2.7.0',
    author='Allan Kilpatrick',
    author_email='allanklp@gmail.com',
    url='http://github.com/allankp/pytest-testrail/',
    packages=[
        'pytest_testrail',
    ],
    package_dir={'pytest_testrail': 'pytest_testrail'},
    install_requires=[
        'pytest>=3.6',
        'requests>=2.20.0',
    ],
    include_package_data=True,
    entry_points={'pytest11': ['pytest-testrail = pytest_testrail.conftest']},
)
