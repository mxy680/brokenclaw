"""Authenticated HTTP client for Canvas REST API.

Uses session cookies captured by canvas_auth.py. Handles CSRF token rotation
and Canvas Link-header pagination.
"""

import re
from urllib.parse import unquote

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.http_client import get_session
from brokenclaw.services.canvas_auth import get_canvas_session


def _build_headers(session_data: dict) -> dict:
    """Construct request headers with session cookies and CSRF token."""
    cookies = "; ".join([
        f"canvas_session={session_data['canvas_session']}",
        f"_csrf_token={session_data.get('_csrf_token', '')}",
        f"log_session_id={session_data.get('log_session_id', '')}",
    ])
    headers = {
        "Cookie": cookies,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
    }
    csrf = session_data.get("_csrf_token", "")
    if csrf:
        headers["X-CSRF-Token"] = unquote(csrf)
    return headers


def _update_csrf_token(response, account: str) -> None:
    """Update stored CSRF token if it rotated in the response cookies."""
    new_csrf = None
    for cookie_str in response.headers.get("Set-Cookie", "").split(","):
        if "_csrf_token=" in cookie_str:
            match = re.search(r"_csrf_token=([^;]+)", cookie_str)
            if match:
                new_csrf = match.group(1)
                break

    if new_csrf:
        store = _get_token_store()
        key = _token_key("canvas", account)
        data = store.get(key)
        if data:
            data["_csrf_token"] = new_csrf
            store.save(key, data)


def _parse_next_link(link_header: str | None) -> str | None:
    """Extract rel='next' URL from Canvas Link header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            match = re.search(r"<(.+?)>", part)
            if match:
                return match.group(1)
    return None


def _handle_response(response, account: str):
    """Check response status and raise appropriate exceptions."""
    _update_csrf_token(response, account)

    if response.status_code == 401:
        raise AuthenticationError(
            "Canvas session expired. Visit /auth/canvas/setup to re-authenticate."
        )
    if response.status_code == 429:
        raise RateLimitError("Canvas API rate limit hit. Wait a moment and retry.")
    if response.status_code >= 400:
        raise IntegrationError(
            f"Canvas API error (HTTP {response.status_code}): {response.text[:500]}"
        )


def canvas_get(path: str, account: str = "default", params: dict | None = None) -> dict | list:
    """Make an authenticated GET request to the Canvas API.

    path should be relative to /api/v1/ (e.g. 'users/self/profile').
    """
    session_data = get_canvas_session(account)
    base_url = session_data["base_url"].rstrip("/")
    url = f"{base_url}/api/v1/{path.lstrip('/')}"
    headers = _build_headers(session_data)

    resp = get_session().get(url, headers=headers, params=params)
    _handle_response(resp, account)
    return resp.json()


def canvas_get_paginated(
    path: str,
    account: str = "default",
    params: dict | None = None,
    max_pages: int = 10,
) -> list:
    """Make paginated GET requests, following Canvas Link headers.

    Returns aggregated list from all pages (up to max_pages).
    """
    session_data = get_canvas_session(account)
    base_url = session_data["base_url"].rstrip("/")
    url = f"{base_url}/api/v1/{path.lstrip('/')}"
    headers = _build_headers(session_data)

    all_items = []
    page_params = dict(params or {})
    page_params.setdefault("per_page", 100)

    for _ in range(max_pages):
        resp = get_session().get(url, headers=headers, params=page_params)
        _handle_response(resp, account)

        data = resp.json()
        if isinstance(data, list):
            all_items.extend(data)
        else:
            all_items.append(data)

        next_url = _parse_next_link(resp.headers.get("Link"))
        if not next_url:
            break
        # Subsequent pages use the full URL from Link header
        url = next_url
        page_params = {}  # params are encoded in the next_url

    return all_items
