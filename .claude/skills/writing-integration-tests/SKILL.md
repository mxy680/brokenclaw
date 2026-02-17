---
name: writing-integration-tests
description: Use when adding or modifying an integration (Gmail, Drive, etc.) and tests are needed. Use when writing tests for services that call external APIs, REST routers, or MCP tools.
---

# Writing Integration Tests

## Overview

Test each integration at three layers: **service** (business logic with mocked API), **router** (HTTP endpoints via FastAPI TestClient), and **MCP tools** (tool functions with mocked service). Every external API call must be mocked — tests must never hit real Google APIs.

## Test Structure

```
tests/
  conftest.py                  # Shared fixtures (mock credentials, token store, test client)
  test_services_<integration>.py   # Service layer tests
  test_routers_<integration>.py    # REST endpoint tests
  test_mcp_<integration>.py        # MCP tool tests
```

## Layer-by-Layer Pattern

### 1. Service Layer Tests (`test_services_*.py`)

Mock the Google API client. Patch `googleapiclient.discovery.build` to return a mock service object that returns canned responses.

**What to test:**
- Each service function returns correct Pydantic model
- Parsing logic handles all message/file fields correctly
- Missing optional fields don't crash (e.g. no body, no parents)
- `HttpError` with status 401 → `AuthenticationError`
- `HttpError` with status 429 → `RateLimitError`
- `HttpError` with other status → `IntegrationError`
- Credentials missing → `AuthenticationError`

**Mock pattern:**
```python
@pytest.fixture
def mock_gmail_service(mocker):
    mock_svc = MagicMock()
    mocker.patch("brokenclaw.services.gmail.get_gmail_credentials")
    mocker.patch("brokenclaw.services.gmail.build", return_value=mock_svc)
    return mock_svc

def test_get_inbox(mock_gmail_service):
    # Set up: configure mock_gmail_service.users().messages().list().execute()
    # Act: call service function
    # Assert: check returned Pydantic models
```

### 2. Router Tests (`test_routers_*.py`)

Use FastAPI `TestClient`. Mock the entire service module so router tests only verify HTTP status codes, response shapes, and query parameter wiring.

**What to test:**
- Each endpoint returns 200 with correct JSON shape
- Query parameters are forwarded to service (max_results, account, query)
- Service exceptions map to correct HTTP status codes (401, 429, 500)

**Mock pattern:**
```python
@pytest.fixture
def client(mocker):
    mocker.patch("brokenclaw.routers.gmail.gmail_service")
    from brokenclaw.main import api
    return TestClient(api)
```

### 3. MCP Tool Tests (`test_mcp_*.py`)

Call tool functions directly. Mock the service module. Verify tools return dicts (not Pydantic models) and handle errors by returning structured error dicts (not raising).

**What to test:**
- Each tool returns a dict with expected keys
- On service exception, tool returns `{"error": ..., "message": ...}` (not raises)
- Account parameter is forwarded to service

## Fixtures to Share (`conftest.py`)

- `mock_credentials` — patches `get_*_credentials` to return a MagicMock
- `mock_token_store` — patches `_get_token_store` with a fake store
- Canned API response dicts for Gmail messages, Drive files

## Checklist Per Integration

- [ ] Service tests: happy path for each function
- [ ] Service tests: error paths (401, 429, generic HttpError)
- [ ] Service tests: edge cases (empty results, missing fields)
- [ ] Router tests: each endpoint returns correct shape
- [ ] Router tests: query params forwarded correctly
- [ ] Router tests: exception → HTTP status mapping
- [ ] MCP tests: each tool returns dict
- [ ] MCP tests: errors return structured error dict (no raise)
- [ ] All mocks prevent real API calls (no network in tests)

## Running Tests

```bash
pytest tests/ -v
```

## Common Mistakes

- Forgetting to mock `build()` — test accidentally calls Google API
- Testing router with real service — should mock service module
- Asserting on MCP tool raising exceptions — tools should catch and return error dicts
- Not testing the `account` parameter forwarding
- Calling MCP tools directly — `@mcp.tool` wraps functions in `FunctionTool` objects; use `tool_name.fn()` to call the underlying function in tests
