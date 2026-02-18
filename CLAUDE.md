# Brokenclaw

Integration server that exposes external platforms via REST API + MCP tools for AI agents.

## IMPORTANT: Always run the server on port 9000, not 8000.

## Architecture

- **Starlette root app** — FastAPI at `/`, FastMCP at `/mcp`, same process/port
- **Service layer** is the source of truth — REST routers and MCP tools are thin wrappers
- **Localhost-only** — middleware rejects non-127.0.0.1 requests
- **OAuth tokens** stored in `tokens.json` (gitignored), keyed by `integration:account`
- **Multi-account** — all OAuth endpoints/tools accept `account` param (defaults to `"default"`)

## Integrations (16)

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

### API-key / feed based (5)
| Integration | Env Var | Key Operations |
|---|---|---|
| Maps/Weather/Timezone | `GOOGLE_MAPS_API_KEY` | geocode, directions, places, weather, forecast, timezone |
| News | `NEWS_API_KEY` | top headlines, search articles |
| GitHub | `GITHUB_TOKEN` | repos, issues, PRs, notifications, search |
| Wolfram Alpha | `WOLFRAM_APP_ID` | structured queries, short answers (math, science, facts) |
| Canvas LMS | `CANVAS_BASE_URL` + session | courses, assignments, grades, announcements, todo, profile (+ iCal fallback via `CANVAS_FEED_URL`) |

### Session-cookie based (2)
| Integration | Auth | Key Operations |
|---|---|---|
| LinkedIn | Playwright login + Voyager API | profile, feed, connections, conversations, messages, notifications, search people/companies/jobs |
| Instagram | Playwright login + private web API | profile, feed, posts, stories, reels, followers/following, saved, DMs (list), search, explore |

## Running

```bash
source .venv/bin/activate
uvicorn brokenclaw.main:app --host 127.0.0.1 --port 9000
```

## Key Files

- `brokenclaw/main.py` — App assembly, middleware, exception handlers
- `brokenclaw/mcp_server.py` — All MCP tools (what Claude sees)
- `brokenclaw/auth.py` — OAuth2 flow + token persistence (Google integrations) + Canvas auth routes
- `brokenclaw/config.py` — pydantic-settings, reads `.env`
- `brokenclaw/exceptions.py` — `AuthenticationError`, `IntegrationError`, `RateLimitError`
- `brokenclaw/services/*.py` — Business logic per integration (shared by REST + MCP)
- `brokenclaw/services/canvas_auth.py` — Playwright-based Canvas login (SSO + Duo MFA), cookie capture
- `brokenclaw/services/canvas_client.py` — Canvas REST API client with session cookies, CSRF rotation, pagination
- `brokenclaw/services/linkedin_auth.py` — Playwright-based LinkedIn login, verification challenge, cookie capture
- `brokenclaw/services/linkedin_client.py` — LinkedIn Voyager API client with session cookies, CSRF token, start/count pagination
- `brokenclaw/services/instagram_auth.py` — Playwright-based Instagram login, 2FA challenge, cookie capture
- `brokenclaw/services/instagram_client.py` — Instagram private web API client with session cookies, CSRF token, cursor pagination
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
   CANVAS_FEED_URL=...
   CANVAS_BASE_URL=https://canvas.case.edu
   LINKEDIN_USERNAME=...
   LINKEDIN_PASSWORD=...
   INSTAGRAM_USERNAME=...
   INSTAGRAM_PASSWORD=...
   ```
3. Install Playwright: `pip install -e . && playwright install chromium`
4. Authenticate Google integrations: `http://localhost:9000/auth/{integration}/setup`
5. Add redirect URIs to Google Cloud Console: `http://localhost:9000/auth/{integration}/callback`
6. Tokens auto-refresh thereafter
7. Canvas session auth: visit `http://localhost:9000/auth/canvas/setup`, complete SSO + Duo MFA in browser
8. LinkedIn session auth: visit `http://localhost:9000/auth/linkedin/setup`, complete any verification challenge in browser
9. Instagram session auth: visit `http://localhost:9000/auth/instagram/setup`, complete any 2FA challenge in browser

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
- `requests`, `icalendar`, `playwright`, and `curl_cffi` are explicit dependencies in pyproject.toml
- Canvas uses Playwright for browser-based session auth (SSO + Duo MFA); session cookies stored in `tokens.json` under `"canvas"` key
- Canvas REST API client uses session cookies + CSRF token rotation, not OAuth
- Canvas auth routes are defined **before** generic `/{integration}` routes in `auth.py` to prevent path conflicts
- LinkedIn uses Playwright for browser-based login; session cookies (`li_at`, `JSESSIONID`) stored in `tokens.json` under `"linkedin"` key
- LinkedIn Voyager API uses `Csrf-Token` header (JSESSIONID without quotes), `X-Restli-Protocol-Version: 2.0.0`, and normalized+json accept header
- LinkedIn requires `curl_cffi` with Chrome TLS impersonation — standard `requests`/`httpx` get detected and session invalidated
- LinkedIn Voyager API has migrated most REST endpoints to GraphQL (`/voyager/api/graphql?queryId=...&variables=(...)`) — GraphQL params need literal parentheses (not URL-encoded), hence `raw_qs` parameter on `linkedin_get()`
- LinkedIn response cookies (especially `__cf_bm` from Cloudflare) must be persisted back to token store after each request
- LinkedIn `get_full_profile()` returns basic profile info but experience/education/skills are empty — LinkedIn serves section data via server-side rendering, not the Voyager API
- LinkedIn job search uses REST endpoint `voyagerJobsDashJobCards`, not the GraphQL search endpoint used by people/company search
- LinkedIn and Canvas and Instagram auth routes are all defined **before** generic `/{integration}` routes in `auth.py`
- Instagram uses Playwright for browser-based login; session cookies (`sessionid`, `csrftoken`, `ds_user_id`) stored in `tokens.json` under `"instagram"` key
- Instagram private web API uses `X-IG-App-ID: 936619743392459`, `X-CSRFToken` header, and `curl_cffi` with Chrome TLS impersonation
- Instagram `csrftoken` rotates frequently in `Set-Cookie` headers — must persist after every request (same as LinkedIn's cookie rotation)
- Instagram API split: most endpoints on `https://i.instagram.com/api/v1/`, search + web profile on `https://www.instagram.com/api/v1/`
- Instagram feed timeline and clips/user (reels) are POST endpoints, not GET
- Instagram uses cursor-based pagination (`next_max_id` / `max_id`), not offset-based
