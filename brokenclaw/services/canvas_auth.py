"""Playwright-based Canvas LMS authentication.

Launches a browser, automates CWRU SSO login, waits for Duo MFA,
then captures session cookies and stores them in tokens.json.
"""

import asyncio

from playwright.async_api import async_playwright

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError


async def _run_login_flow(base_url: str, username: str, password: str) -> dict:
    """Launch Chromium, automate SSO login, wait for Duo MFA, capture cookies.

    Waits up to 5 minutes for MFA completion. Validates session via in-browser
    API call before returning.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("[canvas] Navigating to Canvas...")
        await page.goto(base_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("load")

        # Fill SSO login form (CWRU CAS)
        print("[canvas] Filling SSO credentials...")
        try:
            # Wait for the username field to appear (CAS login page)
            await page.wait_for_selector('input[name="username"], input#username', timeout=15000)
            await page.fill('input[name="username"], input#username', username)
            await page.fill('input[name="password"], input#password', password)

            # Click the login button — try multiple selectors for CAS
            submit = page.locator(
                'button[type="submit"], input[type="submit"], '
                'button[name="submit"], input[name="submit"], '
                'button:has-text("Login"), button:has-text("Log In"), '
                'button:has-text("Sign In"), a:has-text("Login"), '
                'input[value="Login"], input[value="LOG IN"], '
                '.btn-submit, #submit, .login-btn'
            )
            await submit.first.click()
            print("[canvas] Credentials submitted, waiting for Duo MFA...")
        except Exception as e:
            print(f"[canvas] SSO form not found or error: {e}")
            print(f"[canvas] Current URL: {page.url}")

        # After Duo MFA, there may be a "Yes, this is my device" trust prompt
        # Keep checking for it while we wait for login to complete
        trust_clicked = False

        # Wait for Duo MFA + redirect back to Canvas (up to 5 minutes)
        for i in range(300):
            current_url = page.url
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}

            if "canvas_session" in cookie_map and base_url.rstrip("/") in current_url:
                print(f"[canvas] Login complete! URL: {current_url}")
                break

            # Try to click "Yes, this is my device" / trust device button if it appears
            if not trust_clicked:
                try:
                    trust_btn = page.locator(
                        'button:has-text("Yes, this is my device"), '
                        'button:has-text("Trust"), '
                        'button:has-text("Yes"), '
                        'button#trust-browser-button, '
                        'input[value="Yes, this is my device"]'
                    )
                    if await trust_btn.first.is_visible(timeout=500):
                        await trust_btn.first.click()
                        trust_clicked = True
                        print("[canvas] Clicked 'Yes, this is my device'")
                except Exception:
                    pass

            if i % 30 == 0 and i > 0:
                print(f"[canvas] Still waiting for MFA... ({i}s, URL: {current_url[:80]})")

            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError(
                "Login timed out after 5 minutes waiting for Duo MFA."
            )

        # Let the page settle (use "load" — "networkidle" times out on Canvas dashboard)
        await page.wait_for_load_state("load")

        # Validate session by navigating to API endpoint from within the browser
        print("[canvas] Validating session via API...")
        response = await page.goto(
            f"{base_url}/api/v1/users/self/profile",
            wait_until="domcontentloaded",
        )

        status = response.status if response else 0
        body = await page.inner_text("body")

        # Capture all cookies in their final state
        cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in cookies}

        if status == 200:
            print(f"[canvas] API validation OK! Profile: {body[:100]}")
        else:
            print(f"[canvas] API returned {status}: {body[:300]}")
            # Even if API validation fails, store cookies — they may work
            # for other endpoints or the session may need CSRF from HTML

        # Try to get the authenticity token from the Canvas HTML
        # (this is different from the _csrf_token cookie)
        print("[canvas] Extracting CSRF token from Canvas HTML...")
        await page.goto(base_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("load")

        # Canvas puts the CSRF token in a meta tag
        csrf_meta = await page.evaluate("""
            () => {
                const meta = document.querySelector('meta[name="csrf-token"]');
                return meta ? meta.getAttribute('content') : null;
            }
        """)
        print(f"[canvas] CSRF meta token: {csrf_meta[:30] if csrf_meta else 'not found'}...")

        # Re-capture cookies after dashboard load
        cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in cookies}

        await browser.close()

    session_data = {
        "canvas_session": cookie_map.get("canvas_session", ""),
        "_csrf_token": cookie_map.get("_csrf_token", ""),
        "log_session_id": cookie_map.get("log_session_id", ""),
        "csrf_meta_token": csrf_meta or "",
        "all_cookies": cookie_map,
        "base_url": base_url,
        "api_status": status,
    }
    return session_data


def run_canvas_login(
    username: str = "",
    password: str = "",
    account: str = "default",
) -> dict:
    """Run the Playwright login flow and store the session in tokens.json.

    If username/password not provided, falls back to CANVAS_USERNAME/CANVAS_PASSWORD from .env.
    """
    settings = get_settings()
    base_url = settings.canvas_base_url
    if not base_url:
        raise AuthenticationError(
            "CANVAS_BASE_URL not configured. Set it in .env (e.g. https://canvas.case.edu)"
        )
    username = username or settings.canvas_username
    password = password or settings.canvas_password

    session_data = asyncio.run(_run_login_flow(base_url, username, password))

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
