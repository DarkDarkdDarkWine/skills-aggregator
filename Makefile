.PHONY: test test-coverage test-watch install install-test

# Install dependencies
install:
	pip install -r backend/requirements.txt

# Install test dependencies
install-test:
	pip install pytest pytest-asyncio pytest-cov httpx aiosqlite

# Run all tests
test:
	cd backend && python -m pytest tests/ -v

# Run tests with coverage
test-coverage:
	cd backend && python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Run tests in watch mode
test-watch:
	cd backend && ptw tests/ -- -v

# Run specific test file
test-file:
	cd backend && python -m pytest tests/$(FILE) -v

# Run tests by pattern
test-pattern:
	cd backend && python -m pytest tests/ -k "$(PATTERN)" -v

# Lint and format check
lint:
	cd backend && python -m ruff check app/
	cd backend && python -m black --check app/

# Type check
typecheck:
	cd backend && python -m mypy app/
