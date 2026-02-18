"""Authenticated HTTP client for Slack web API.

Uses session cookies (d cookie with xoxd- value) and xoxc- client token
captured by slack_auth.py. All Slack API methods are POST-based with
form-encoded params.

Uses curl_cffi with browser TLS fingerprint impersonation to avoid detection.
Response cookies are persisted back to the token store after each request.
"""

import re

from curl_cffi import requests as curl_requests

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.services.slack_auth import get_slack_session

BASE_URL = "https://slack.com/api"


def _build_headers(session_data: dict) -> dict:
    """Construct request headers with session token and cookies.

    xoxc- token goes in Authorization header, d cookie goes in Cookie header.
    Both are required for every request.
    """
    d_cookie = session_data.get("d_cookie", "")
    all_cookies = session_data.get("all_cookies", {})

    if all_cookies:
        cookies = "; ".join(f"{k}={v}" for k, v in all_cookies.items())
    else:
        cookies = f"d={d_cookie}"

    return {
        "Cookie": cookies,
        "Authorization": f"Bearer {session_data.get('xoxc_token', '')}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }


def _update_cookies(response, account: str) -> None:
    """Persist any Set-Cookie values back to the token store."""
    new_cookies = {}
    set_cookie_headers = []
    for k, v in response.headers.items():
        if k.lower() == "set-cookie":
            set_cookie_headers.append(v)

    for cookie_str in set_cookie_headers:
        match = re.match(r"([^=]+)=([^;]*)", cookie_str)
        if match:
            name, value = match.group(1).strip(), match.group(2).strip()
            new_cookies[name] = value

    if new_cookies:
        store = _get_token_store()
        key = _token_key("slack", account)
        data = store.get(key)
        if data and "all_cookies" in data:
            data["all_cookies"].update(new_cookies)
            if "d" in new_cookies and new_cookies["d"].startswith("xoxd-"):
                data["d_cookie"] = new_cookies["d"]
            store.save(key, data)


def _handle_response(response) -> dict:
    """Check HTTP status and Slack API ok field, raise appropriate exceptions."""
    if response.status_code in (401, 403):
        raise AuthenticationError(
            "Slack session expired. Visit /auth/slack/setup to re-authenticate."
        )
    if response.status_code == 429:
        raise RateLimitError("Slack API rate limit hit. Wait a moment and retry.")
    if response.status_code >= 400:
        raise IntegrationError(
            f"Slack API error (HTTP {response.status_code}): {response.text[:500]}"
        )

    data = response.json()

    if not data.get("ok"):
        error = data.get("error", "unknown_error")
        if error in ("not_authed", "invalid_auth", "token_revoked", "token_expired"):
            raise AuthenticationError(
                f"Slack auth error: {error}. Visit /auth/slack/setup to re-authenticate."
            )
        if error == "ratelimited":
            raise RateLimitError("Slack API rate limit hit. Wait a moment and retry.")
        raise IntegrationError(f"Slack API error: {error}")

    return data


def slack_api(
    method: str,
    account: str = "default",
    params: dict | None = None,
) -> dict:
    """Make an authenticated POST request to a Slack API method.

    method should be the API method name (e.g. 'auth.test', 'conversations.list').
    params are sent as form-encoded POST body.
    """
    session_data = get_slack_session(account)
    url = f"{BASE_URL}/{method}"
    headers = _build_headers(session_data)

    resp = curl_requests.post(
        url,
        headers=headers,
        data=params or {},
        impersonate="chrome",
        allow_redirects=False,
    )
    _update_cookies(resp, account)
    return _handle_response(resp)


def slack_api_paginated(
    method: str,
    account: str = "default",
    params: dict | None = None,
    result_key: str = "members",
    count: int = 100,
    max_pages: int = 5,
) -> list:
    """Make paginated Slack API requests using cursor-based pagination.

    Returns all items from the result_key across pages.
    """
    all_items = []
    page_params = dict(params or {})
    page_params["limit"] = count

    for _ in range(max_pages):
        data = slack_api(method, account, page_params)
        items = data.get(result_key, [])
        all_items.extend(items)

        cursor = (data.get("response_metadata") or {}).get("next_cursor", "")
        if not cursor:
            break
        page_params["cursor"] = cursor

    return all_items
