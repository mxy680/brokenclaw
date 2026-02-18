"""Slack OAuth2 flow — separate from Google auth since Slack uses a different OAuth provider."""

import json
from urllib.parse import urlencode

import requests
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError
from brokenclaw.models.common import StatusResponse

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"

# User-level scopes for personal assistant use
SLACK_USER_SCOPES = [
    "channels:read",
    "channels:history",
    "groups:read",
    "groups:history",
    "im:read",
    "im:history",
    "mpim:read",
    "mpim:history",
    "chat:write",
    "search:read",
    "users:read",
    "users:read.email",
    "reactions:write",
    "reactions:read",
    "files:read",
]


def _get_slack_config():
    settings = get_settings()
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise AuthenticationError(
            "Slack credentials not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in .env"
        )
    return settings.slack_client_id, settings.slack_client_secret


def _redirect_uri() -> str:
    settings = get_settings()
    return f"http://localhost:{settings.port}/auth/slack/callback"


def _token_store_key() -> str:
    return "slack"


def get_slack_token() -> str:
    """Get the stored Slack user token. Raises if not authenticated."""
    from brokenclaw.auth import _get_token_store
    store = _get_token_store()
    data = store.get(_token_store_key())
    if not data or "access_token" not in data:
        raise AuthenticationError(
            "Slack not authenticated. Visit /auth/slack/setup to connect."
        )
    return data["access_token"]


def has_slack_token() -> bool:
    """Check if a Slack token exists."""
    from brokenclaw.auth import _get_token_store
    store = _get_token_store()
    data = store.get(_token_store_key())
    return bool(data and data.get("access_token"))


# --- Slack auth router ---

router = APIRouter(prefix="/auth/slack", tags=["auth"])


@router.get("/setup")
def slack_auth_setup():
    """Redirect to Slack OAuth consent screen."""
    client_id, _ = _get_slack_config()
    params = {
        "client_id": client_id,
        "user_scope": ",".join(SLACK_USER_SCOPES),
        "redirect_uri": _redirect_uri(),
    }
    return RedirectResponse(f"{SLACK_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/callback")
def slack_auth_callback(code: str):
    """Handle OAuth callback from Slack, exchange code for token."""
    client_id, client_secret = _get_slack_config()
    resp = requests.post(SLACK_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": _redirect_uri(),
    })
    data = resp.json()
    if not data.get("ok"):
        return StatusResponse(
            integration="slack",
            authenticated=False,
            message=f"Slack auth failed: {data.get('error', 'unknown error')}",
        )
    # Extract user token from authed_user
    authed_user = data.get("authed_user", {})
    token_data = {
        "access_token": authed_user.get("access_token"),
        "user_id": authed_user.get("id"),
        "scope": authed_user.get("scope"),
        "team_id": data.get("team", {}).get("id"),
        "team_name": data.get("team", {}).get("name"),
    }
    from brokenclaw.auth import _get_token_store
    store = _get_token_store()
    store.save(_token_store_key(), token_data)
    team_name = token_data.get("team_name", "workspace")
    return StatusResponse(
        integration="slack",
        authenticated=True,
        message=f"Slack authenticated for {team_name}. You can close this tab.",
    )


@router.get("/status")
def slack_auth_status() -> StatusResponse:
    """Check whether Slack has a valid token."""
    valid = has_slack_token()
    return StatusResponse(
        integration="slack",
        authenticated=valid,
        message="Authenticated" if valid else "Not authenticated — visit /auth/slack/setup",
    )
