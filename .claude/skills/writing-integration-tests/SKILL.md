---
name: writing-integration-tests
description: Use when adding or modifying an integration (Gmail, Drive, Sheets, etc.) and tests are needed. Use when writing tests for services that call real external APIs like Google.
---

# Writing Integration Tests

## Overview

Test each integration against the **real API**. Tests must authenticate with stored credentials and hit live Google endpoints. If credentials aren't available, tests skip gracefully. Write operations must clean up after themselves.

## Test Structure

```
tests/
  conftest.py                  # Skip markers based on auth status
  test_<integration>.py        # Real API tests per integration
```

One test file per integration. No mocks, no fakes — real API calls.

## Core Principles

1. **Real API calls only** — tests hit live Google APIs with stored OAuth tokens
2. **Skip if not authenticated** — use `pytest.mark.skipif` so unauthenticated integrations don't fail
3. **Clean up write operations** — delete files, trash messages, remove spreadsheets after tests
4. **Use pytest fixtures** — `autouse=True` fixtures for setup/teardown of resources
5. **Validate Pydantic models** — assert returned objects are correct model types with expected fields

## Skip Markers (`conftest.py`)

```python
import pytest
from brokenclaw.auth import _get_token_store

def _is_authenticated(integration: str) -> bool:
    store = _get_token_store()
    return store.has_valid_token(integration)

requires_gmail = pytest.mark.skipif(
    not _is_authenticated("gmail"),
    reason="Gmail not authenticated — run /auth/gmail/setup first",
)
```

Create one `requires_*` marker per integration. Apply as class decorator.

## Test Patterns

### Read-only tests

Query the real API and validate the shape of results:

```python
@requires_drive
class TestListFiles:
    def test_returns_list_of_files(self):
        files = drive_service.list_files(max_results=3)
        assert isinstance(files, list)
        assert len(files) <= 3
        if files:
            assert isinstance(files[0], DriveFile)
            assert files[0].id
```

### Write tests with cleanup

Create a resource, validate it, then delete it — always clean up:

```python
@requires_drive
class TestCreateAndReadFile:
    def test_create_read_delete_file(self):
        created = drive_service.create_file(
            name="brokenclaw_test_file.txt",
            content="Hello from tests!",
            mime_type="text/plain",
        )
        assert isinstance(created, DriveFile)
        try:
            content = drive_service.get_file_content(created.id)
            assert content.content == "Hello from tests!"
        finally:
            _delete_file(created.id)
```

Use `try/finally` or `pytest.fixture(autouse=True)` with `yield` for cleanup.

### Fixture-based cleanup

For tests that share a resource across multiple test methods:

```python
@requires_sheets
class TestReadWriteAppend:
    @pytest.fixture(autouse=True)
    def setup_spreadsheet(self):
        self.spreadsheet = sheets_service.create_spreadsheet(
            title="brokenclaw_test_rw", sheet_names=["TestSheet"],
        )
        yield
        _delete_spreadsheet(self.spreadsheet.id)
```

## Cleanup Helpers

Each integration needs a cleanup function using the lowest-level API:

- **Gmail**: `service.users().messages().trash(userId="me", id=msg_id).execute()`
- **Drive**: `service.files().delete(fileId=file_id).execute()`
- **Sheets**: Delete via Drive API (Sheets API can't delete spreadsheets)

## Checklist Per Integration

- [ ] Skip marker in `conftest.py` checking auth status
- [ ] Read tests: validate return types and field presence
- [ ] Read tests: respect `max_results` parameter
- [ ] Search tests: both matching and non-matching queries
- [ ] Write tests: create, validate, clean up
- [ ] All write operations cleaned up in `finally` or fixture teardown
- [ ] Prefix test resource names with `brokenclaw_test_` for easy identification

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

Unauthenticated integrations will show as SKIPPED, not FAILED.

## Common Mistakes

- Not cleaning up created resources — pollutes the real account
- Using `maxResults=0` — Gmail API rejects this, use `maxResults=1` instead
- Importing from `tests.conftest` — use `from conftest import` (pytest handles it)
- Forgetting `try/finally` around write test assertions — cleanup won't run on failure
- Not checking if inbox is empty before fetching by ID — use `pytest.skip("Inbox is empty")`
