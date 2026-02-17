# Brokenclaw

Integration server that exposes external platforms (Gmail) via REST API + MCP tools.

## Architecture

- **Starlette root app** — FastAPI at `/`, FastMCP at `/mcp`, same process/port
- **Service layer** is the source of truth — REST routers and MCP tools are thin wrappers
- **Localhost-only** — middleware rejects non-127.0.0.1 requests
- **OAuth tokens** stored in `tokens.json` (gitignored), keyed by integration name

## Running

```bash
source .venv/bin/activate
uvicorn brokenclaw.main:app --host 127.0.0.1 --port 8000
```

## Key Files

- `brokenclaw/main.py` — App assembly, middleware, exception handlers
- `brokenclaw/mcp_server.py` — FastMCP tools (what Claude sees)
- `brokenclaw/services/gmail.py` — Gmail business logic (shared by REST + MCP)
- `brokenclaw/auth.py` — OAuth2 flow + token persistence
- `brokenclaw/config.py` — pydantic-settings, reads `.env`

## Setup

1. Place `client_secret.json` from Google Cloud Console in project root
2. Visit `http://localhost:8000/auth/gmail/setup` to authenticate
3. Token auto-refreshes thereafter

## MCP Configuration

For Claude Code, add to MCP settings:
```json
{
  "mcpServers": {
    "brokenclaw": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Conventions

- Exceptions: `AuthenticationError`, `IntegrationError`, `RateLimitError` in `exceptions.py`
- Service functions return Pydantic models; MCP tools serialize to dicts
- MCP tools catch service exceptions and return structured error dicts (agent-friendly)
- REST endpoints let exceptions propagate to FastAPI exception handlers
