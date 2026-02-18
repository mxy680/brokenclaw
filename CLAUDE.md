# Brokenclaw

Integration server that exposes external platforms via REST API + MCP tools for AI agents.

## IMPORTANT: Always run the server on port 9000, not 8000.

## Architecture

- **Starlette root app** — FastAPI at `/`, FastMCP at `/mcp`, same process/port
- **Service layer** is the source of truth — REST routers and MCP tools are thin wrappers
- **Localhost-only** — middleware rejects non-127.0.0.1 requests
- **OAuth tokens** stored in `tokens.json` (gitignored), keyed by `integration:account`
- **Multi-account** — all OAuth endpoints/tools accept `account` param (defaults to `"default"`)

## Integrations (13)

### Google OAuth-based (9)
| Integration | Scope | Key Operations |
|---|---|---|
| Gmail | gmail.readonly, send, modify | inbox, search, read, send, reply |
| Drive | drive | list, search, read, create files/folders |
| Sheets | spreadsheets | read/write ranges, append rows, create |
| Docs | documents | read, create, insert text, find/replace |
| Slides | presentations | read, create, add slides, find/replace |
| Tasks | tasks | lists, create/update/complete/delete tasks |
| Forms | forms.body, forms.responses | create forms, add questions, read responses |
| YouTube | youtube.readonly | search, video/channel details, playlists |
| Calendar | calendar | list/create/update/delete events, quick add |

### API-key based (4)
| Integration | Env Var | Key Operations |
|---|---|---|
| Maps/Weather/Timezone | `GOOGLE_MAPS_API_KEY` | geocode, directions, places, weather, forecast, timezone |
| News | `NEWS_API_KEY` | top headlines, search articles |
| GitHub | `GITHUB_TOKEN` | repos, issues, PRs, notifications, search |
| Wolfram Alpha | `WOLFRAM_APP_ID` | structured queries, short answers (math, science, facts) |

## Running

```bash
source .venv/bin/activate
uvicorn brokenclaw.main:app --host 127.0.0.1 --port 9000
```

## Key Files

- `brokenclaw/main.py` — App assembly, middleware, exception handlers
- `brokenclaw/mcp_server.py` — All MCP tools (what Claude sees)
- `brokenclaw/auth.py` — OAuth2 flow + token persistence (Google integrations)
- `brokenclaw/config.py` — pydantic-settings, reads `.env`
- `brokenclaw/exceptions.py` — `AuthenticationError`, `IntegrationError`, `RateLimitError`
- `brokenclaw/services/*.py` — Business logic per integration (shared by REST + MCP)
- `brokenclaw/models/*.py` — Pydantic models per integration
- `brokenclaw/routers/*.py` — REST endpoints per integration

## Setup

1. Place `client_secret.json` from Google Cloud Console in project root
2. Create `.env` with API keys:
   ```
   GOOGLE_MAPS_API_KEY=...
   NEWS_API_KEY=...
   GITHUB_TOKEN=...
   WOLFRAM_APP_ID=...
   ```
3. Authenticate Google integrations: `http://localhost:9000/auth/{integration}/setup`
4. Add redirect URIs to Google Cloud Console: `http://localhost:9000/auth/{integration}/callback`
5. Tokens auto-refresh thereafter

## Adding Integrations

**OAuth-based (Google):**
1. Add scopes to `INTEGRATION_SCOPES` in `auth.py`
2. Add `get_{name}_credentials()` in `auth.py`
3. Create `models/{name}.py`, `services/{name}.py`, `routers/{name}.py`
4. Add MCP tools in `mcp_server.py`
5. Include router in `main.py`
6. Add `requires_{name}` marker in `tests/conftest.py`

**API-key based:**
1. Add config field in `config.py`
2. Create `models/{name}.py`, `services/{name}.py`, `routers/{name}.py`
3. Add MCP tools in `mcp_server.py`
4. Include router in `main.py`
5. Add status check in `brokenclaw_status()` tool

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

- Service functions return Pydantic models; MCP tools serialize to dicts
- MCP tools catch service exceptions and return structured error dicts (agent-friendly)
- REST endpoints let exceptions propagate to FastAPI exception handlers
- OAuth client is a **web** type (not desktop) — uses redirect-based flow
- `OAUTHLIB_RELAX_TOKEN_SCOPE` is set to handle Google returning broader scopes
- API-key integrations use `requests` library directly (not googleapiclient)
- `requests` is a transitive dependency (via google-auth) — not listed explicitly in pyproject.toml
