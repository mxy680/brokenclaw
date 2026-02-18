"""Authenticated HTTP client for LinkedIn Voyager API.

Uses session cookies captured by linkedin_auth.py. Handles Voyager-specific
response format with `included` entities and `start`/`count` pagination.
"""

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.http_client import get_session
from brokenclaw.services.linkedin_auth import get_linkedin_session

BASE_URL = "https://www.linkedin.com/voyager/api"

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _build_headers(session_data: dict) -> dict:
    """Construct request headers with session cookies and CSRF token."""
    all_cookies = session_data.get("all_cookies", {})
    if all_cookies:
        cookies = "; ".join(f"{k}={v}" for k, v in all_cookies.items())
    else:
        cookies = "; ".join([
            f"li_at={session_data['li_at']}",
            f"JSESSIONID={session_data.get('JSESSIONID', '')}",
        ])
    return {
        "Cookie": cookies,
        "Csrf-Token": session_data.get("csrf_token", ""),
        "X-Restli-Protocol-Version": "2.0.0",
        "X-Li-Lang": "en_US",
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "User-Agent": _USER_AGENT,
    }


def _handle_response(response):
    """Check response status and raise appropriate exceptions."""
    if response.status_code == 401:
        raise AuthenticationError(
            "LinkedIn session expired. Visit /auth/linkedin/setup to re-authenticate."
        )
    if response.status_code == 429:
        raise RateLimitError("LinkedIn API rate limit hit. Wait a moment and retry.")
    if response.status_code >= 400:
        raise IntegrationError(
            f"LinkedIn API error (HTTP {response.status_code}): {response.text[:500]}"
        )


def _extract_voyager_entities(data: dict, entity_type: str) -> list[dict]:
    """Extract entities from Voyager `included` array by $type suffix.

    Voyager responses have `included` (flat entity list) and `data` (metadata).
    entity_type is matched against the end of the $type field,
    e.g. 'com.linkedin.voyager.identity.shared.MiniProfile' matches 'MiniProfile'.
    """
    included = data.get("included", [])
    return [
        item for item in included
        if item.get("$type", "").endswith(entity_type)
    ]


def linkedin_get(
    path: str,
    account: str = "default",
    params: dict | None = None,
) -> dict:
    """Make an authenticated GET request to the LinkedIn Voyager API.

    path should be relative to /voyager/api/ (e.g. 'me').
    """
    session_data = get_linkedin_session(account)
    url = f"{BASE_URL}/{path.lstrip('/')}"
    headers = _build_headers(session_data)

    resp = get_session().get(url, headers=headers, params=params)
    _handle_response(resp)
    return resp.json()


def linkedin_get_paginated(
    path: str,
    account: str = "default",
    params: dict | None = None,
    count: int = 20,
    max_pages: int = 5,
) -> list[dict]:
    """Make paginated GET requests using LinkedIn's start/count pagination.

    Returns the raw JSON responses (each containing `included` and `data`).
    Caller is responsible for extracting entities.
    """
    session_data = get_linkedin_session(account)
    headers = _build_headers(session_data)

    all_included = []
    page_params = dict(params or {})
    page_params["count"] = count
    start = page_params.pop("start", 0)

    for _ in range(max_pages):
        page_params["start"] = start
        url = f"{BASE_URL}/{path.lstrip('/')}"
        resp = get_session().get(url, headers=headers, params=page_params)
        _handle_response(resp)

        data = resp.json()
        included = data.get("included", [])
        all_included.extend(included)

        # Check if there are more pages
        paging = data.get("data", {}).get("paging") or data.get("paging", {})
        total = paging.get("total", 0)
        start += count
        if start >= total:
            break

    return all_included
