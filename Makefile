.PHONY: init init-dev test

init:
	pip install -r requirements.txt

init-dev:
	pip install -r requirements/dev.txt

test:
	pytest

test-cov:
	pytest -v --cov=vandockit
