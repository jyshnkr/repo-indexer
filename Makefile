.PHONY: test test-cov lint lint-py

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=skills/repo-indexer/scripts --cov-report=term-missing

lint: lint-py

lint-py:
	flake8 skills/repo-indexer/scripts/ --max-line-length=120
