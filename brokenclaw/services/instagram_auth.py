"""Playwright-based Instagram authentication.

Launches a browser, automates Instagram login, waits for any 2FA
challenge (user enters code manually), then captures session cookies
and stores them in tokens.json.
"""

import asyncio

from playwright.async_api import async_playwright

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError


async def _run_login_flow(username: str, password: str) -> dict:
    """Launch Chromium, automate Instagram login, capture session cookies.

    Waits up to 5 minutes for any 2FA challenge to be completed
    manually by the user.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("[instagram] Navigating to Instagram login...")
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        await page.wait_for_load_state("load")

        # Fill login form
        print("[instagram] Filling credentials...")
        try:
            await page.wait_for_selector('input[name="username"]', timeout=15000)
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            print("[instagram] Credentials submitted...")
        except Exception as e:
            print(f"[instagram] Login form error: {e}")
            print(f"[instagram] Current URL: {page.url}")

        # Wait for login to complete (may involve 2FA challenge)
        print("[instagram] Waiting for login (complete any 2FA challenge in the browser)...")
        for i in range(300):
            current_url = page.url
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}

            if "sessionid" in cookie_map and "/accounts/login" not in current_url:
                print(f"[instagram] Login complete! URL: {current_url}")
                break

            if i % 30 == 0 and i > 0:
                print(f"[instagram] Still waiting... ({i}s, URL: {current_url[:80]})")

            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError(
                "Instagram login timed out after 5 minutes."
            )

        # Validate session via in-page fetch
        print("[instagram] Validating session via Instagram API...")
        validation = await page.evaluate("""
            async () => {
                try {
                    const resp = await fetch('https://i.instagram.com/api/v1/accounts/current_user/?edit=true', {
                        headers: {
                            'X-IG-App-ID': '936619743392459',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        credentials: 'include',
                    });
                    const text = await resp.text();
                    return { status: resp.status, body: text.substring(0, 2000) };
                } catch (e) {
                    return { status: 0, body: e.message };
                }
            }
        """)

        status = validation.get("status", 0)
        body = validation.get("body", "")

        if status == 200:
            print(f"[instagram] API validation OK! Profile: {body[:100]}")
        else:
            print(f"[instagram] API returned {status}: {body[:300]}")

        # Re-capture cookies after API call
        raw_cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in raw_cookies}

        cookie_details = [
            {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]}
            for c in raw_cookies
        ]

        await browser.close()

    session_data = {
        "sessionid": cookie_map.get("sessionid", ""),
        "csrftoken": cookie_map.get("csrftoken", ""),
        "ds_user_id": cookie_map.get("ds_user_id", ""),
        "mid": cookie_map.get("mid", ""),
        "ig_did": cookie_map.get("ig_did", ""),
        "all_cookies": cookie_map,
        "cookie_details": cookie_details,
        "api_status": status,
    }
    return session_data


def run_instagram_login(
    username: str = "",
    password: str = "",
    account: str = "default",
) -> dict:
    """Run the Playwright login flow and store the session in tokens.json."""
    settings = get_settings()
    username = username or settings.instagram_username
    password = password or settings.instagram_password

    if not username or not password:
        raise AuthenticationError(
            "Instagram credentials not configured. Set INSTAGRAM_USERNAME and "
            "INSTAGRAM_PASSWORD in .env, or pass them as parameters."
        )

    session_data = asyncio.run(_run_login_flow(username, password))

    store = _get_token_store()
    key = _token_key("instagram", account)
    store.save(key, session_data)

    return session_data


def get_instagram_session(account: str = "default") -> dict:
    """Load stored Instagram session from token store.

    Raises AuthenticationError if no session exists.
    """
    store = _get_token_store()
    key = _token_key("instagram", account)
    data = store.get(key)
    if not data or "sessionid" not in data:
        raise AuthenticationError(
            f"Instagram not authenticated (account={account}). "
            f"Visit /auth/instagram/setup?account={account} to log in via browser."
        )
    return data


def has_instagram_session(account: str = "default") -> bool:
    """Check whether an Instagram session exists in the token store."""
    store = _get_token_store()
    key = _token_key("instagram", account)
    data = store.get(key)
    return bool(data and data.get("sessionid"))
