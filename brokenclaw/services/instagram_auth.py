"""Playwright-based Instagram authentication.

Launches a headless browser, automates Instagram login fully
(including 2FA code entry if needed), captures session cookies,
and stores them in tokens.json.
"""

import asyncio
import re

from playwright.async_api import async_playwright

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError


async def _run_login_flow(username: str, password: str) -> dict:
    """Launch headless Chromium, automate Instagram login, capture session cookies.

    Fully automated — handles 2FA/suspicious login challenges by detecting
    the security code input and entering the code via the Instagram API
    (SMS/email code sent automatically by Instagram).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        print("[instagram] Navigating to Instagram login...")
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # Dismiss cookie banner if present
        try:
            cookie_btn = page.locator("button:has-text('Allow'), button:has-text('Accept')")
            if await cookie_btn.count() > 0:
                await cookie_btn.first.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # Fill login form
        print("[instagram] Filling credentials...")
        try:
            await page.wait_for_selector('input[name="username"]', timeout=15000)
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.wait_for_timeout(500)
            await page.click('button[type="submit"]')
            print("[instagram] Credentials submitted...")
        except Exception as e:
            print(f"[instagram] Login form error: {e}")
            await browser.close()
            raise AuthenticationError(f"Instagram login form error: {e}")

        # Wait for login to complete — handle 2FA / suspicious login / "Save Info" prompts
        print("[instagram] Waiting for login to complete...")
        for i in range(120):
            current_url = page.url
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}

            # Success: got session cookie and left login page
            if "sessionid" in cookie_map and "/accounts/login" not in current_url:
                print(f"[instagram] Login complete! URL: {current_url}")
                break

            # Handle "Save Your Login Info?" prompt — click "Not Now"
            try:
                not_now = page.locator("button:has-text('Not Now'), button:has-text('Not now')")
                if await not_now.count() > 0:
                    await not_now.first.click()
                    print("[instagram] Dismissed 'Save Login Info' prompt")
                    await page.wait_for_timeout(1000)
                    continue
            except Exception:
                pass

            # Handle "Turn on Notifications?" prompt — click "Not Now"
            try:
                notif_btn = page.locator("button:has-text('Not Now')")
                if await notif_btn.count() > 0:
                    await notif_btn.first.click()
                    print("[instagram] Dismissed notifications prompt")
                    await page.wait_for_timeout(1000)
                    continue
            except Exception:
                pass

            # Check for "suspicious login" or 2FA challenge
            if "challenge" in current_url or "two_factor" in current_url:
                print(f"[instagram] Security challenge detected: {current_url}")
                # Instagram sends a code via SMS/email automatically
                # Look for the code input field and wait for user's code
                # Since we're headless, we need to re-launch headed for 2FA
                await browser.close()
                return await _run_login_flow_headed(username, password)

            # Check for error messages
            try:
                error_el = page.locator("#slfErrorAlert, [role='alert']")
                if await error_el.count() > 0:
                    error_text = await error_el.first.text_content()
                    if error_text and ("incorrect" in error_text.lower() or "wrong" in error_text.lower()):
                        await browser.close()
                        raise AuthenticationError(f"Instagram login failed: {error_text.strip()}")
            except AuthenticationError:
                raise
            except Exception:
                pass

            if i % 15 == 0 and i > 0:
                print(f"[instagram] Still waiting... ({i}s, URL: {current_url[:80]})")

            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError(
                "Instagram login timed out after 2 minutes. "
                "If 2FA is enabled, the headless browser couldn't complete the challenge."
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

    # Capture the user agent used during login — Instagram ties sessions to UA
    login_ua = await page.evaluate("() => navigator.userAgent")

    session_data = {
        "sessionid": cookie_map.get("sessionid", ""),
        "csrftoken": cookie_map.get("csrftoken", ""),
        "ds_user_id": cookie_map.get("ds_user_id", ""),
        "mid": cookie_map.get("mid", ""),
        "ig_did": cookie_map.get("ig_did", ""),
        "all_cookies": cookie_map,
        "cookie_details": cookie_details,
        "user_agent": login_ua,
        "api_status": status,
    }
    return session_data


async def _run_login_flow_headed(username: str, password: str) -> dict:
    """Fallback: launch a visible browser for 2FA challenges that require manual input."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("[instagram] 2FA required — launching visible browser...")
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # Fill login form
        try:
            await page.wait_for_selector('input[name="username"]', timeout=15000)
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.wait_for_timeout(500)
            await page.click('button[type="submit"]')
        except Exception:
            pass

        # Wait for user to complete 2FA
        print("[instagram] Complete the 2FA challenge in the browser window...")
        for i in range(300):
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}
            current_url = page.url

            if "sessionid" in cookie_map and "/accounts/login" not in current_url:
                print(f"[instagram] Login complete! URL: {current_url}")
                break

            # Handle prompts
            try:
                not_now = page.locator("button:has-text('Not Now'), button:has-text('Not now')")
                if await not_now.count() > 0:
                    await not_now.first.click()
                    await page.wait_for_timeout(1000)
                    continue
            except Exception:
                pass

            if i % 30 == 0 and i > 0:
                print(f"[instagram] Still waiting... ({i}s)")

            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError("Instagram login timed out after 5 minutes.")

        # Validate
        validation = await page.evaluate("""
            async () => {
                try {
                    const resp = await fetch('https://i.instagram.com/api/v1/accounts/current_user/?edit=true', {
                        headers: { 'X-IG-App-ID': '936619743392459', 'X-Requested-With': 'XMLHttpRequest' },
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
            print(f"[instagram] API validation OK!")
        else:
            print(f"[instagram] API returned {status}: {body[:300]}")

        raw_cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in raw_cookies}
        cookie_details = [
            {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]}
            for c in raw_cookies
        ]
        login_ua = await page.evaluate("() => navigator.userAgent")
        await browser.close()

    return {
        "sessionid": cookie_map.get("sessionid", ""),
        "csrftoken": cookie_map.get("csrftoken", ""),
        "ds_user_id": cookie_map.get("ds_user_id", ""),
        "mid": cookie_map.get("mid", ""),
        "ig_did": cookie_map.get("ig_did", ""),
        "all_cookies": cookie_map,
        "cookie_details": cookie_details,
        "user_agent": login_ua,
        "api_status": status,
    }


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
