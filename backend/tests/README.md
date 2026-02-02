# Tests

## Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_api.py::TestSourceEndpoints

# Run with verbose output
pytest -v
```

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_models.py           # Data model tests
├── test_ai_provider.py      # AI Provider service tests
├── test_github.py           # GitHub service tests
├── test_analyzer.py         # AI analyzer tests
├── test_sync.py             # Sync service tests
└── test_api.py              # API route tests
```

## Writing Tests

### Unit Tests
- Use `pytest` and `pytest-asyncio` for async tests
- Mock external dependencies with `unittest.mock`
- Use fixtures from `conftest.py`

### Integration Tests
- Use `TestClient` for API testing
- Use in-memory SQLite for database tests

### Example

```python
import pytest
from app.main import app

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
```
