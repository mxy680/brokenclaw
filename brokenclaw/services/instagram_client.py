"""Authenticated HTTP client for Instagram web API.

Uses session cookies captured by instagram_auth.py. All endpoints go through
www.instagram.com (the web API), NOT i.instagram.com (the mobile API which
rejects web-session user agents).

Uses curl_cffi with browser TLS fingerprint impersonation — Instagram rejects
requests from standard HTTP libraries by detecting non-browser TLS fingerprints
(same pattern as LinkedIn). Do NOT set a custom User-Agent header — let
curl_cffi's impersonation handle it; setting an explicit UA causes
"useragent mismatch" errors because Instagram checks the TLS-level fingerprint.

Response cookies (especially csrftoken) are persisted back to the token store
after each request so subsequent calls stay authenticated.
"""

import re

from curl_cffi import requests as curl_requests

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.services.instagram_auth import get_instagram_session

BASE_URL = "https://www.instagram.com/api/v1"


def _build_headers(session_data: dict) -> dict:
    """Construct request headers with session cookies and CSRF token.

    Does NOT set User-Agent — curl_cffi's impersonate="chrome" handles that,
    and Instagram validates the UA against the TLS fingerprint.
    """
    all_cookies = session_data.get("all_cookies", {})
    if all_cookies:
        cookies = "; ".join(f"{k}={v}" for k, v in all_cookies.items())
    else:
        cookies = "; ".join([
            f"sessionid={session_data['sessionid']}",
            f"csrftoken={session_data.get('csrftoken', '')}",
            f"ds_user_id={session_data.get('ds_user_id', '')}",
            f"mid={session_data.get('mid', '')}",
            f"ig_did={session_data.get('ig_did', '')}",
        ])
    return {
        "Cookie": cookies,
        "X-CSRFToken": session_data.get("csrftoken", ""),
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Referer": "https://www.instagram.com/",
    }


def _update_cookies(response, account: str) -> None:
    """Persist any Set-Cookie values (especially csrftoken) back to the token store."""
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
        key = _token_key("instagram", account)
        data = store.get(key)
        if data and "all_cookies" in data:
            data["all_cookies"].update(new_cookies)
            if "csrftoken" in new_cookies:
                data["csrftoken"] = new_cookies["csrftoken"]
            store.save(key, data)


def _handle_response(response):
    """Check response status and raise appropriate exceptions."""
    if response.status_code in (401, 403):
        raise AuthenticationError(
            "Instagram session expired. Visit /auth/instagram/setup to re-authenticate."
        )
    if response.status_code == 429:
        raise RateLimitError("Instagram API rate limit hit. Wait a moment and retry.")
    if response.status_code >= 400:
        raise IntegrationError(
            f"Instagram API error (HTTP {response.status_code}): {response.text[:500]}"
        )


def instagram_get(
    path: str,
    account: str = "default",
    params: dict | None = None,
    base_url: str | None = None,
) -> dict:
    """Make an authenticated GET request to the Instagram web API.

    path should be relative to the base URL (e.g. 'accounts/current_user/').
    """
    session_data = get_instagram_session(account)
    url = f"{base_url or BASE_URL}/{path.lstrip('/')}"
    headers = _build_headers(session_data)

    resp = curl_requests.get(
        url,
        headers=headers,
        params=params,
        impersonate="chrome",
        allow_redirects=False,
    )
    _update_cookies(resp, account)
    _handle_response(resp)
    return resp.json()


def instagram_post(
    path: str,
    account: str = "default",
    data: dict | None = None,
    params: dict | None = None,
    base_url: str | None = None,
) -> dict:
    """Make an authenticated POST request to the Instagram web API.

    Used for endpoints like feed/timeline/ and clips/user/ that require POST.
    """
    session_data = get_instagram_session(account)
    url = f"{base_url or BASE_URL}/{path.lstrip('/')}"
    headers = _build_headers(session_data)

    resp = curl_requests.post(
        url,
        headers=headers,
        data=data,
        params=params,
        impersonate="chrome",
        allow_redirects=False,
    )
    _update_cookies(resp, account)
    _handle_response(resp)
    return resp.json()


def instagram_get_paginated(
    path: str,
    account: str = "default",
    params: dict | None = None,
    count: int = 20,
    max_pages: int = 3,
    base_url: str | None = None,
) -> tuple[list, str | None]:
    """Make paginated GET requests using Instagram's cursor-based pagination.

    Returns (all_items, next_cursor). Instagram uses `next_max_id` or `max_id`
    in responses for cursor-based pagination.
    """
    all_items = []
    cursor = None
    page_params = dict(params or {})
    page_params["count"] = count

    for _ in range(max_pages):
        if cursor:
            page_params["max_id"] = cursor

        session_data = get_instagram_session(account)
        headers = _build_headers(session_data)
        url = f"{base_url or BASE_URL}/{path.lstrip('/')}"

        resp = curl_requests.get(
            url,
            headers=headers,
            params=page_params,
            impersonate="chrome",
            allow_redirects=False,
        )
        _update_cookies(resp, account)
        _handle_response(resp)

        data = resp.json()
        items = data.get("items", [])
        all_items.extend(items)

        cursor = data.get("next_max_id")
        if not cursor or not data.get("more_available", False):
            break

    return all_items, cursor
