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

        # Capture cookies with full metadata (domain, path, etc.)
        raw_cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in raw_cookies}

        # Validate session via in-page fetch (preserves browser session context)
        print("[linkedin] Validating session via Voyager API...")
        jsessionid = cookie_map.get("JSESSIONID", "")
        csrf_token = jsessionid.strip('"')

        validation = await page.evaluate("""
            async (csrfToken) => {
                try {
                    const resp = await fetch('/voyager/api/me', {
                        headers: {
                            'Csrf-Token': csrfToken,
                            'X-Restli-Protocol-Version': '2.0.0',
                            'Accept': 'application/vnd.linkedin.normalized+json+2.1',
                        },
                        credentials: 'include',
                    });
                    const text = await resp.text();
                    return { status: resp.status, body: text.substring(0, 2000) };
                } catch (e) {
                    return { status: 0, body: e.message };
                }
            }
        """, csrf_token)

        status = validation.get("status", 0)
        body = validation.get("body", "")

        if status == 200:
            print(f"[linkedin] API validation OK! Profile: {body[:100]}")
        else:
            print(f"[linkedin] API returned {status}: {body[:300]}")

        # Re-capture cookies after API call
        raw_cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in raw_cookies}

        # Also store raw cookies with domain info for proper reconstruction
        cookie_details = [
            {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]}
            for c in raw_cookies
        ]

        await browser.close()

    jsessionid = cookie_map.get("JSESSIONID", "")
    csrf_token = jsessionid.strip('"')

    session_data = {
        "li_at": cookie_map.get("li_at", ""),
        "JSESSIONID": jsessionid,
        "csrf_token": csrf_token,
        "all_cookies": cookie_map,
        "cookie_details": cookie_details,
        "api_status": status,
        "api_body": body[:500] if status == 200 else "",
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
