requirements:
	pip install -r requirements-dev.txt

test:
	python -m pytest --cov=arq_admin --cov-fail-under 100 --cov-report term-missing

coverage-collect:
	coverage run -m pytest

coverage-report:
	coverage html

coverage: coverage-collect coverage-report

mypy:
	mypy arq_admin tests *.py

flake8:
	flake8 .

isort:
	isort .

bandit:
	bandit -q -r .

check: isort flake8 mypy bandit test
