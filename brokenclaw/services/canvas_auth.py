"""Playwright-based Canvas LMS authentication.

Launches a visible browser for the user to complete SSO + Duo MFA,
then captures session cookies and stores them in tokens.json.
"""

import asyncio

from playwright.async_api import async_playwright

from brokenclaw.auth import TokenStore, _get_token_store, _token_key
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError


async def _run_login_flow(base_url: str) -> dict:
    """Launch Chromium, navigate to Canvas, wait for user to complete SSO + Duo MFA.

    Returns dict with canvas_session, _csrf_token, log_session_id, and all cookies.
    Waits up to 5 minutes for the canvas_session cookie to appear.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(base_url, wait_until="domcontentloaded")

        # Wait for the user to complete SSO + Duo MFA (up to 5 minutes)
        # We know login is complete when canvas_session cookie appears
        for _ in range(300):  # 300 seconds = 5 minutes
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}
            if "canvas_session" in cookie_map:
                break
            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError(
                "Login timed out after 5 minutes. "
                "Please try again and complete SSO + Duo MFA in the browser window."
            )

        # Extract all relevant cookies
        cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in cookies}
        await browser.close()

    session_data = {
        "canvas_session": cookie_map.get("canvas_session", ""),
        "_csrf_token": cookie_map.get("_csrf_token", ""),
        "log_session_id": cookie_map.get("log_session_id", ""),
        "base_url": base_url,
    }
    return session_data


def run_canvas_login(account: str = "default") -> dict:
    """Run the Playwright login flow and store the session in tokens.json.

    Returns the session data dict on success.
    """
    settings = get_settings()
    base_url = settings.canvas_base_url
    if not base_url:
        raise AuthenticationError(
            "CANVAS_BASE_URL not configured. Set it in .env (e.g. https://canvas.case.edu)"
        )

    session_data = asyncio.run(_run_login_flow(base_url))

    store = _get_token_store()
    key = _token_key("canvas", account)
    store.save(key, session_data)

    return session_data


def get_canvas_session(account: str = "default") -> dict:
    """Load stored Canvas session from token store.

    Raises AuthenticationError if no session exists.
    """
    store = _get_token_store()
    key = _token_key("canvas", account)
    data = store.get(key)
    if not data or "canvas_session" not in data:
        raise AuthenticationError(
            f"Canvas not authenticated (account={account}). "
            f"Visit /auth/canvas/setup?account={account} to log in via browser."
        )
    return data


def has_canvas_session(account: str = "default") -> bool:
    """Check whether a Canvas session exists in the token store."""
    store = _get_token_store()
    key = _token_key("canvas", account)
    data = store.get(key)
    return bool(data and data.get("canvas_session"))
