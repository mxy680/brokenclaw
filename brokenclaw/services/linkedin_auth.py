"""Playwright-based LinkedIn authentication.

Launches a browser, automates LinkedIn login, waits for any verification
challenge (email/phone PIN), then captures session cookies and stores them
in tokens.json.
"""

import asyncio

from playwright.async_api import async_playwright

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError


async def _run_login_flow(username: str, password: str) -> dict:
    """Launch Chromium, automate LinkedIn login, capture session cookies.

    Waits up to 5 minutes for any verification challenge to be completed
    manually by the user.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("[linkedin] Navigating to LinkedIn login...")
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        await page.wait_for_load_state("load")

        # Fill login form
        print("[linkedin] Filling credentials...")
        try:
            await page.wait_for_selector("input#username", timeout=15000)
            await page.fill("input#username", username)
            await page.fill("input#password", password)
            await page.click('button[type="submit"]')
            print("[linkedin] Credentials submitted...")
        except Exception as e:
            print(f"[linkedin] Login form error: {e}")
            print(f"[linkedin] Current URL: {page.url}")

        # Wait for login to complete (may involve verification challenge)
        print("[linkedin] Waiting for login (complete any verification challenge in the browser)...")
        for i in range(300):
            current_url = page.url
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}

            if "li_at" in cookie_map and ("/feed" in current_url or "/mynetwork" in current_url or "/messaging" in current_url):
                print(f"[linkedin] Login complete! URL: {current_url}")
                break

            if i % 30 == 0 and i > 0:
                print(f"[linkedin] Still waiting... ({i}s, URL: {current_url[:80]})")

            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError(
                "LinkedIn login timed out after 5 minutes."
            )

        # Validate session via Voyager API
        print("[linkedin] Validating session via Voyager API...")
        response = await page.goto(
            "https://www.linkedin.com/voyager/api/me",
            wait_until="domcontentloaded",
        )
        status = response.status if response else 0
        body = await page.inner_text("body")

        if status == 200:
            print(f"[linkedin] API validation OK! Profile: {body[:100]}")
        else:
            print(f"[linkedin] API returned {status}: {body[:300]}")

        # Capture final cookies
        cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in cookies}

        await browser.close()

    # Extract JSESSIONID and derive csrf_token (JSESSIONID without quotes)
    jsessionid = cookie_map.get("JSESSIONID", "")
    csrf_token = jsessionid.strip('"')

    session_data = {
        "li_at": cookie_map.get("li_at", ""),
        "JSESSIONID": jsessionid,
        "csrf_token": csrf_token,
        "all_cookies": cookie_map,
        "api_status": status,
    }
    return session_data


def run_linkedin_login(
    username: str = "",
    password: str = "",
    account: str = "default",
) -> dict:
    """Run the Playwright login flow and store the session in tokens.json."""
    settings = get_settings()
    username = username or settings.linkedin_username
    password = password or settings.linkedin_password

    if not username or not password:
        raise AuthenticationError(
            "LinkedIn credentials not configured. Set LINKEDIN_USERNAME and "
            "LINKEDIN_PASSWORD in .env, or pass them as parameters."
        )

    session_data = asyncio.run(_run_login_flow(username, password))

    store = _get_token_store()
    key = _token_key("linkedin", account)
    store.save(key, session_data)

    return session_data


def get_linkedin_session(account: str = "default") -> dict:
    """Load stored LinkedIn session from token store.

    Raises AuthenticationError if no session exists.
    """
    store = _get_token_store()
    key = _token_key("linkedin", account)
    data = store.get(key)
    if not data or "li_at" not in data:
        raise AuthenticationError(
            f"LinkedIn not authenticated (account={account}). "
            f"Visit /auth/linkedin/setup?account={account} to log in via browser."
        )
    return data


def has_linkedin_session(account: str = "default") -> bool:
    """Check whether a LinkedIn session exists in the token store."""
    store = _get_token_store()
    key = _token_key("linkedin", account)
    data = store.get(key)
    return bool(data and data.get("li_at"))
