.PHONY: test test-cov lint lint-py lint-sh

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=skills/repo-indexer/scripts --cov-report=term-missing

lint: lint-py lint-sh

lint-py:
	flake8 skills/repo-indexer/scripts/ --max-line-length=120

lint-sh:
	shellcheck skills/repo-indexer/scripts/git-sync.sh
