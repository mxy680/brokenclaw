"""Playwright-based Slack authentication.

Launches a headed browser, automates SSO login (CWRU CAS), waits for Duo MFA,
then captures the `d` cookie (xoxd-) and `xoxc-` client token from localStorage.
The only manual step is approving the Duo push notification.
"""

import asyncio

from playwright.async_api import async_playwright

from brokenclaw.auth import _get_token_store, _token_key
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError


async def _run_login_flow(workspace_url: str, email: str, password: str) -> dict:
    """Launch headed Chromium, automate SSO login, wait for Duo MFA, capture session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"[slack] Navigating to {workspace_url}...")
        await page.goto(workspace_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("load")

        # --- Phase 1: Fill credentials (SSO/CAS or Slack-native) ---
        print("[slack] Looking for login form...")
        try:
            # Wait for any login form to appear
            await page.wait_for_selector(
                'input[name="username"], input#username, '
                'input[type="email"], input[name="email"], input#email',
                timeout=15000,
            )

            # SSO/CAS form (e.g. CWRU) — uses username/password fields
            sso_username = page.locator('input[name="username"], input#username')
            if await sso_username.count() > 0:
                print("[slack] Detected SSO login form, filling credentials...")
                await sso_username.first.fill(email)
                await page.fill('input[name="password"], input#password', password)
            else:
                # Slack-native email/password form
                print("[slack] Detected Slack login form, filling credentials...")
                email_input = page.locator('input[type="email"], input[name="email"], input#email')
                if await email_input.count() > 0:
                    await email_input.first.fill(email)
                    await page.wait_for_timeout(500)
                    submit_btn = page.locator(
                        'button[type="submit"], button:has-text("Continue"), '
                        'button:has-text("Sign In"), button:has-text("Next")'
                    )
                    if await submit_btn.count() > 0:
                        await submit_btn.first.click()
                        await page.wait_for_timeout(2000)

                password_input = page.locator('input[type="password"], input[name="password"]')
                if await password_input.count() > 0:
                    await password_input.first.fill(password)

            # Click submit
            submit = page.locator(
                'button[type="submit"], input[type="submit"], '
                'button[name="submit"], input[name="submit"], '
                'button:has-text("Login"), button:has-text("Log In"), '
                'button:has-text("Sign In"), button:has-text("Sign in"), '
                'input[value="Login"], input[value="LOG IN"], '
                '.btn-submit, #submit'
            )
            if await submit.count() > 0:
                await submit.first.click()
                print("[slack] Credentials submitted, waiting for Duo MFA...")
            else:
                print("[slack] No submit button found, pressing Enter...")
                await page.keyboard.press("Enter")
                print("[slack] Credentials submitted, waiting for Duo MFA...")

        except Exception as e:
            print(f"[slack] Login form error: {e}")
            print(f"[slack] Current URL: {page.url}")
            print("[slack] Complete login manually in the browser window...")

        # --- Phase 2: Wait for Duo MFA + Slack app to load ---
        trust_clicked = False
        xoxc_token = None
        d_cookie = None

        for i in range(300):  # 5 minutes
            # Auto-click "Yes, this is my device" trust button after Duo
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
                        print("[slack] Clicked 'Yes, this is my device'")
                except Exception:
                    pass

            # Try to extract xoxc token from localStorage
            try:
                token = await page.evaluate("""
                    () => {
                        try {
                            const config = JSON.parse(localStorage.getItem('localConfig_v2'));
                            if (config && config.teams) {
                                const teamKeys = Object.keys(config.teams);
                                if (teamKeys.length > 0) {
                                    return config.teams[teamKeys[0]].token || null;
                                }
                            }
                        } catch (e) {}
                        return null;
                    }
                """)
                if token and token.startswith("xoxc-"):
                    xoxc_token = token
                    print(f"[slack] Got xoxc token: {token[:20]}...")
            except Exception:
                pass

            # Check for d cookie
            cookies = await context.cookies()
            cookie_map = {c["name"]: c["value"] for c in cookies}
            if "d" in cookie_map and cookie_map["d"].startswith("xoxd-"):
                d_cookie = cookie_map["d"]

            if xoxc_token and d_cookie:
                print("[slack] Login complete! Got both xoxc token and d cookie.")
                break

            if i % 30 == 0 and i > 0:
                print(f"[slack] Still waiting... ({i}s, URL: {page.url[:80]})")

            await page.wait_for_timeout(1000)
        else:
            await browser.close()
            raise AuthenticationError("Slack login timed out after 5 minutes.")

        # --- Phase 3: Capture session data ---
        raw_cookies = await context.cookies()
        cookie_map = {c["name"]: c["value"] for c in raw_cookies}
        cookie_details = [
            {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]}
            for c in raw_cookies
        ]

        team_id = None
        user_id = None
        try:
            auth_info = await page.evaluate("""
                () => {
                    try {
                        const config = JSON.parse(localStorage.getItem('localConfig_v2'));
                        if (config && config.teams) {
                            const teamKeys = Object.keys(config.teams);
                            if (teamKeys.length > 0) {
                                const team = config.teams[teamKeys[0]];
                                return { team_id: teamKeys[0], user_id: team.user_id || null };
                            }
                        }
                    } catch (e) {}
                    return {};
                }
            """)
            team_id = auth_info.get("team_id")
            user_id = auth_info.get("user_id")
        except Exception:
            pass

        await browser.close()

    return {
        "xoxc_token": xoxc_token,
        "d_cookie": d_cookie,
        "team_id": team_id,
        "user_id": user_id,
        "all_cookies": cookie_map,
        "cookie_details": cookie_details,
    }


def run_slack_login(
    workspace_url: str = "",
    email: str = "",
    password: str = "",
    account: str = "default",
) -> dict:
    """Run the Playwright login flow and store the session in tokens.json."""
    settings = get_settings()
    workspace_url = workspace_url or settings.slack_workspace_url
    email = email or settings.slack_email
    password = password or settings.slack_password

    if not workspace_url:
        raise AuthenticationError(
            "Slack workspace URL not configured. Set SLACK_WORKSPACE_URL in .env "
            "(e.g. https://myteam.slack.com)."
        )
    if not email or not password:
        raise AuthenticationError(
            "Slack credentials not configured. Set SLACK_EMAIL and "
            "SLACK_PASSWORD in .env, or pass them as parameters."
        )

    session_data = asyncio.run(_run_login_flow(workspace_url, email, password))

    if not session_data.get("xoxc_token") or not session_data.get("d_cookie"):
        raise AuthenticationError(
            "Failed to capture Slack session tokens. Try running again or "
            "check your credentials."
        )

    # Validate session via auth.test
    from curl_cffi import requests as curl_requests

    headers = {
        "Authorization": f"Bearer {session_data['xoxc_token']}",
        "Cookie": f"d={session_data['d_cookie']}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = curl_requests.post(
        "https://slack.com/api/auth.test",
        headers=headers,
        impersonate="chrome",
    )
    result = resp.json()
    if result.get("ok"):
        session_data["team_id"] = result.get("team_id", session_data.get("team_id"))
        session_data["user_id"] = result.get("user_id", session_data.get("user_id"))
        session_data["team_name"] = result.get("team")
        print(f"[slack] Validated! Team: {result.get('team')}, User: {result.get('user')}")
    else:
        print(f"[slack] auth.test failed: {result.get('error')} — session may still work")

    store = _get_token_store()
    key = _token_key("slack", account)
    store.save(key, session_data)

    return session_data


def get_slack_session(account: str = "default") -> dict:
    """Load stored Slack session from token store.

    Raises AuthenticationError if no session exists.
    """
    store = _get_token_store()
    key = _token_key("slack", account)
    data = store.get(key)
    if not data or not data.get("xoxc_token") or not data.get("d_cookie"):
        raise AuthenticationError(
            f"Slack not authenticated (account={account}). "
            f"Visit /auth/slack/setup?account={account} to log in via browser."
        )
    return data


def has_slack_session(account: str = "default") -> bool:
    """Check whether a Slack session exists in the token store."""
    store = _get_token_store()
    key = _token_key("slack", account)
    data = store.get(key)
    return bool(data and data.get("xoxc_token") and data.get("d_cookie"))
