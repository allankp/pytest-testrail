
define HELP

This is the pytest testrail project Makefile.

Usage:
make clean        - Remove generated files
make coverage     - Run coverage analysis
make lint         - Run static analysis
make release      - Bumpversion and push with tags
make requirements - Install dependencies
make test         - Run static analysis, tests with coverage

endef

export HELP

all help:
	@echo "$$HELP"

clean:
	rm -rf .cache .coverage .tox pytests_py*-test.xml pytest_testrail.egg-info pytest_testrail.txt pytests_coverage.xml
	find . -name '*.pyc' -delete

coverage:
	tox -e coverage

lint:
	flake8 pytest_testrail | tee pytest_testrail.txt

README.rst: README.md
	pandoc --from=markdown --to=rst --output=README.rst README.md

release:
	bump2version part $(type)
	git push origin master --tags

requirements: .requirements.txt

.requirements.txt: requirements/*.txt
	pip install -r requirements/base.txt
	pip freeze > $@

test: coverage lint
	tox
