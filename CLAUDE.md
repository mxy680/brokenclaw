# Brokenclaw

Integration server that exposes external platforms (Gmail, Google Drive, Sheets, Docs, Slides, Tasks) via REST API + MCP tools.

## IMPORTANT: Always run the server on port 9000, not 8000.

## Architecture

- **Starlette root app** — FastAPI at `/`, FastMCP at `/mcp`, same process/port
- **Service layer** is the source of truth — REST routers and MCP tools are thin wrappers
- **Localhost-only** — middleware rejects non-127.0.0.1 requests
- **OAuth tokens** stored in `tokens.json` (gitignored), keyed by `integration:account`
- **Multi-account** — all endpoints/tools accept `account` param (defaults to `"default"`)

## Running

```bash
source .venv/bin/activate
uvicorn brokenclaw.main:app --host 127.0.0.1 --port 9000
```

## Key Files

- `brokenclaw/main.py` — App assembly, middleware, exception handlers
- `brokenclaw/mcp_server.py` — FastMCP tools (what Claude sees)
- `brokenclaw/services/gmail.py` — Gmail business logic (shared by REST + MCP)
- `brokenclaw/services/drive.py` — Google Drive business logic (shared by REST + MCP)
- `brokenclaw/services/sheets.py` — Google Sheets business logic (shared by REST + MCP)
- `brokenclaw/services/docs.py` — Google Docs business logic (shared by REST + MCP)
- `brokenclaw/services/slides.py` — Google Slides business logic (shared by REST + MCP)
- `brokenclaw/services/tasks.py` — Google Tasks business logic (shared by REST + MCP)
- `brokenclaw/auth.py` — OAuth2 flow + token persistence (generalized for all integrations)
- `brokenclaw/config.py` — pydantic-settings, reads `.env`

## Setup

1. Place `client_secret.json` from Google Cloud Console in project root
2. Visit `http://localhost:9000/auth/gmail/setup` to authenticate Gmail
3. Visit `http://localhost:9000/auth/drive/setup` to authenticate Drive
3b. Similarly for Sheets, Docs, Slides, Tasks: `http://localhost:9000/auth/{integration}/setup`
4. Add redirect URIs to Google Cloud Console: `http://localhost:9000/auth/{integration}/callback`
5. Tokens auto-refresh thereafter

## Adding Integrations

Pattern for each integration:
1. Add scopes to `INTEGRATION_SCOPES` in `auth.py`
2. Add `get_{name}_credentials()` in `auth.py`
3. Create `models/{name}.py`, `services/{name}.py`, `routers/{name}.py`
4. Add MCP tools in `mcp_server.py`
5. Include router in `main.py`

## MCP Configuration

For Claude Code, add to MCP settings:
```json
{
  "mcpServers": {
    "brokenclaw": {
      "url": "http://localhost:9000/mcp"
    }
  }
}
```

## Conventions

- Exceptions: `AuthenticationError`, `IntegrationError`, `RateLimitError` in `exceptions.py`
- Service functions return Pydantic models; MCP tools serialize to dicts
- MCP tools catch service exceptions and return structured error dicts (agent-friendly)
- REST endpoints let exceptions propagate to FastAPI exception handlers
- Auth is generalized: `INTEGRATION_SCOPES` dict, `_get_credentials(integration, account)` handles all
- OAuth client is a **web** type (not desktop) — uses redirect-based flow, not `InstalledAppFlow`
- `OAUTHLIB_RELAX_TOKEN_SCOPE` is set to handle Google returning broader scopes than requested
