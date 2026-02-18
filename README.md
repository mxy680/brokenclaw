# Brokenclaw

An integration server that gives AI agents hands. Brokenclaw exposes 18 external platforms through a unified REST API and 117 MCP tools — letting Claude, GPT, and other LLMs read your email, search Google Drive, post to Slack, manage GitHub issues, and much more, all from a single localhost server.

```
┌─────────────────────────────────────────────────────┐
│                    AI Agent                          │
│              (Claude, GPT, etc.)                     │
└──────────────┬──────────────────┬───────────────────┘
               │ MCP (tools)      │ REST API
               ▼                  ▼
┌─────────────────────────────────────────────────────┐
│                   Brokenclaw                         │
│          localhost:9000  ·  single process           │
│                                                      │
│   ┌─────────┐  ┌──────────┐  ┌───────────────────┐  │
│   │  OAuth   │  │ API Keys │  │ Session Cookies   │  │
│   │ (Google) │  │          │  │ (Playwright auth) │  │
│   └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│        ▼             ▼                  ▼             │
│   Gmail Drive   GitHub News    LinkedIn Instagram    │
│   Sheets Docs   Maps Wolfram   Canvas Slack          │
│   Slides Tasks  YouTube                              │
│   Forms Calendar                                     │
│   Gemini                                             │
└─────────────────────────────────────────────────────┘
```

## Features

- **117 MCP tools** — every integration exposed as callable tools for AI agents
- **123 REST endpoints** — full HTTP API with OpenAPI docs at `/docs`
- **Multi-account** — connect multiple accounts per integration (e.g. personal + work Gmail)
- **Localhost-only** — middleware rejects all non-127.0.0.1 requests
- **Three auth strategies** — OAuth2, API keys, and browser-based session cookies
- **Auto-refresh tokens** — OAuth tokens refresh transparently; no manual re-auth
- **Structured errors** — MCP tools return agent-friendly error dicts with suggested actions

## Integrations

### Google OAuth (9 integrations)

| Integration | What it can do |
|---|---|
| **Gmail** | Inbox, search, read full messages, send, reply, modify labels |
| **Drive** | List, search, read, create files and folders |
| **Sheets** | Read/write cell ranges, append rows, create spreadsheets |
| **Docs** | Read content, create documents, insert text, find/replace |
| **Slides** | Read presentations, create decks, add slides, find/replace |
| **Tasks** | Task lists, create/update/complete/delete tasks |
| **Forms** | Create forms, add questions, read responses |
| **YouTube** | Search videos, get video/channel details, list playlists |
| **Calendar** | List/create/update/delete events, quick add |

### API Key & Feed Based (6 integrations)

| Integration | What it can do |
|---|---|
| **Maps / Weather / Timezone** | Geocode, directions, nearby places, current weather, forecasts, timezone lookup |
| **News** | Top headlines, search articles by keyword/source/date |
| **GitHub** | Repos, issues, PRs, notifications, code search |
| **Wolfram Alpha** | Structured queries, short answers — math, science, facts |
| **Canvas LMS** | Courses, assignments, grades, announcements, todo, profile (+ iCal feed) |
| **Gemini** | Analyze images and videos from any platform URL via Google's Gemini models |

### Session-Cookie Based (3 integrations)

These use Playwright to automate browser login, then operate via private APIs.

| Integration | What it can do |
|---|---|
| **LinkedIn** | Profile, feed, connections, conversations, messages, notifications, search people/companies/jobs |
| **Instagram** | Profile, feed, posts, stories, reels, followers/following, saved, DMs, search, explore |
| **Slack** | Profile, conversations, messages, threads, search, users |

## Quick Start

### Prerequisites

- Python 3.11+
- A [Google Cloud Console](https://console.cloud.google.com/) project with the APIs you want enabled
- API keys for any key-based integrations you want to use

### Install

```bash
git clone https://github.com/yourname/brokenclaw.git
cd brokenclaw
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium   # needed for LinkedIn, Instagram, Slack, Canvas auth
```

### Configure

1. Download `client_secret.json` from Google Cloud Console (OAuth 2.0 Client ID, **Web application** type) and place it in the project root.

2. Create a `.env` file:

```env
# Google API key integrations
GOOGLE_MAPS_API_KEY=your-key
GEMINI_API_KEY=your-key

# Third-party API keys
NEWS_API_KEY=your-key
GITHUB_TOKEN=ghp_your-token
WOLFRAM_APP_ID=your-app-id

# Canvas LMS
CANVAS_BASE_URL=https://your-school.instructure.com
CANVAS_FEED_URL=https://your-school.instructure.com/feeds/calendars/...

# LinkedIn (for browser-based auth)
LINKEDIN_USERNAME=you@email.com
LINKEDIN_PASSWORD=your-password

# Instagram (for browser-based auth)
INSTAGRAM_USERNAME=your-username
INSTAGRAM_PASSWORD=your-password

# Slack (for browser-based auth)
SLACK_WORKSPACE_URL=https://your-workspace.slack.com
SLACK_EMAIL=you@email.com
SLACK_PASSWORD=your-password
```

3. Add OAuth redirect URIs in Google Cloud Console for each Google integration:
```
http://localhost:9000/auth/gmail/callback
http://localhost:9000/auth/drive/callback
http://localhost:9000/auth/sheets/callback
...
```

### Run

```bash
source .venv/bin/activate
uvicorn brokenclaw.main:app --host 127.0.0.1 --port 9000
```

Or with Docker:

```bash
docker compose up
```

### Authenticate

**Google integrations** — visit the setup URL in your browser:
```
http://localhost:9000/auth/gmail/setup
http://localhost:9000/auth/drive/setup
...
```
Complete the OAuth flow once. Tokens auto-refresh after that.

**Session-based integrations** — visit the setup URL, then complete login in the Playwright browser:
```
http://localhost:9000/auth/linkedin/setup
http://localhost:9000/auth/instagram/setup
http://localhost:9000/auth/slack/setup
http://localhost:9000/auth/canvas/setup
```

**Check status** of all integrations:
```
GET http://localhost:9000/api/status
```

## Usage with AI Agents

### Claude Code (MCP)

Add to your MCP settings (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "brokenclaw": {
      "url": "http://localhost:9000/mcp"
    }
  }
}
```

Claude can then call tools like `gmail_inbox`, `drive_search`, `github_list_issues`, etc.

### REST API

All integrations are available as standard HTTP endpoints:

```bash
# Read your inbox
curl http://localhost:9000/gmail/inbox

# Search Google Drive
curl "http://localhost:9000/drive/search?query=quarterly%20report"

# Send an email
curl -X POST http://localhost:9000/gmail/send \
  -H "Content-Type: application/json" \
  -d '{"to": "alice@example.com", "subject": "Hello", "body": "Hi from Brokenclaw"}'

# Check GitHub notifications
curl http://localhost:9000/github/notifications
```

Interactive API docs are available at `http://localhost:9000/docs`.

## Architecture

```
brokenclaw/
├── main.py              # Starlette root app — mounts FastAPI + FastMCP
├── mcp_server.py        # 117 MCP tool definitions
├── auth.py              # OAuth2 flows + token persistence
├── config.py            # pydantic-settings, reads .env
├── exceptions.py        # AuthenticationError, IntegrationError, RateLimitError
├── http_client.py       # Shared HTTP client utilities
├── models/              # Pydantic models per integration
├── services/            # Business logic (shared by REST + MCP)
│   ├── gmail.py
│   ├── drive.py
│   ├── linkedin_auth.py # Playwright-based browser auth
│   ├── linkedin_client.py # Voyager API client (curl_cffi)
│   └── ...
├── routers/             # REST endpoints per integration
│   ├── gmail.py
│   ├── drive.py
│   └── ...
tests/                   # Integration tests per service
```

The service layer is the source of truth. REST routers and MCP tools are thin wrappers that delegate to services, keeping business logic in one place.

## Testing

```bash
pip install -e ".[test]"
pytest
```

Tests hit real external APIs and require active authentication. Use pytest markers to run specific integration tests:

```bash
pytest tests/test_gmail.py
pytest tests/test_github.py
```

## License

Private project. All rights reserved.
