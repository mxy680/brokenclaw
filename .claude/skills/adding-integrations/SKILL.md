---
name: adding-integrations
description: Use when adding a new Google integration (e.g. Slides, Calendar, Tasks) to Brokenclaw. Covers the full flow from auth registration through testing and server restart.
---

# Adding Integrations to Brokenclaw

## Overview

Each integration follows an identical pattern: auth scope, credentials helper, models, service, router, MCP tools, mount, tests. After implementation, restart the server and authenticate both accounts.

## Implementation Steps

### 1. Auth (`brokenclaw/auth.py`)
- Add `"<name>": ["https://www.googleapis.com/auth/<scope>"]` to `INTEGRATION_SCOPES`
- Add `get_<name>_credentials(account)` function (one-liner calling `_get_credentials`)

### 2. Models (`brokenclaw/models/<name>.py`)
- Pydantic models for responses and request bodies
- Follow existing patterns in `models/docs.py` or `models/sheets.py`

### 3. Service (`brokenclaw/services/<name>.py`)
- `_get_<name>_service(account)` — builds API client with `build("<api>", "<version>", credentials=creds)`
- `_handle_api_error(e)` — standard 429/401/403 handling
- Business logic functions returning Pydantic models
- All functions take `account: str = "default"` as last param

### 4. Router (`brokenclaw/routers/<name>.py`)
- `APIRouter(prefix="/api/<name>", tags=["<name>"])`
- Thin wrappers calling service functions

### 5. MCP Tools (`brokenclaw/mcp_server.py`)
- Import service module
- Add `@mcp.tool` functions prefixed with `<name>_`
- Wrap in `try/except (AuthenticationError, IntegrationError, RateLimitError)` returning `_handle_mcp_error(e)`
- Include helpful docstrings — these are what Claude sees

### 6. Mount (`brokenclaw/main.py`)
- Import and `api.include_router(<name>_router)`

### 7. Tests
- Add `requires_<name>` skip marker in `tests/conftest.py`
- Create `tests/test_<name>.py` following `writing-integration-tests` skill
- Clean up created resources via Drive API in `finally` blocks

## Post-Implementation Checklist

### Restart server
Kill and restart — the running server has old code:
```bash
kill $(lsof -ti :9000) && sleep 1
source .venv/bin/activate
nohup uvicorn brokenclaw.main:app --host 127.0.0.1 --port 9000 > /dev/null 2>&1 &
```

### Authenticate BOTH accounts
The user has two Google accounts. Set up both:
1. `http://localhost:9000/auth/<name>/setup` (default account)
2. `http://localhost:9000/auth/<name>/setup?account=school` (school account)

Remind the user to complete both before running tests.

### Enable the API
Remind the user to enable the relevant Google API in Google Cloud Console if not already enabled.

### Run full test suite
Run ALL integration tests, not just the new ones — verify no regressions:
```bash
.venv/bin/python -m pytest tests/ -v
```
All previous integration tests must still pass. New tests will skip until authenticated.

### Commit
Commit after verification passes.

### Update CLAUDE.md
Add the new service to the Key Files section and description.
