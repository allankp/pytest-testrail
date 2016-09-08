from setuptools import setup

setup(
    name='pytest-testrail',
    description='pytest plugin for creating TestRail runs and adding results',
    version='0.0.4',
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
        'requests'
    ],
    include_package_data=True,
    entry_points={'pytest11': ['pytest-testrail = pytest_testrail.conftest']},
)
