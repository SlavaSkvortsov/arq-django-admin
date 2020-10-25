requirements:
	pip install -r requirements-dev.txt

test:
	pytest --cov=arq_admin --cov-fail-under 100

coverage-collect:
	coverage run -m pytest

coverage-report:
	coverage html

coverage: coverage-collect coverage-report

mypy:
	mypy .

flake8:
	flake8 .

isort:
	isort .

bandit:
	bandit -q -r .

safety:
	safety check --bare --full-report -r requirements.txt -r requirements-dev.txt

check: isort flake8 mypy bandit safety test
