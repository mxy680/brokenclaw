import json
import os
from pathlib import Path

# Allow Google to return broader scopes than requested (e.g. from prior grants)
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from brokenclaw.config import get_settings
from brokenclaw.models.common import StatusResponse

INTEGRATION_SCOPES = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive",
    ],
}

SUPPORTED_INTEGRATIONS = set(INTEGRATION_SCOPES.keys())


def _token_key(integration: str, account: str) -> str:
    """Build token store key: 'gmail' for default, 'gmail:name' otherwise."""
    return integration if account == "default" else f"{integration}:{account}"


def _redirect_uri(integration: str) -> str:
    settings = get_settings()
    return f"http://localhost:{settings.port}/auth/{integration}/callback"


class TokenStore:
    """Reads/writes OAuth tokens to a local JSON file, keyed by integration:account."""

    def __init__(self, path: Path):
        self.path = path

    def _read_all(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def get(self, key: str) -> dict | None:
        return self._read_all().get(key)

    def save(self, key: str, token_data: dict) -> None:
        all_tokens = self._read_all()
        all_tokens[key] = token_data
        self.path.write_text(json.dumps(all_tokens, indent=2))

    def has_valid_token(self, key: str) -> bool:
        token_data = self.get(key)
        if not token_data:
            return False
        creds = Credentials.from_authorized_user_info(token_data)
        return creds.valid or (creds.expired and creds.refresh_token)

    def list_accounts(self, integration: str) -> list[str]:
        """Return all authenticated account names for an integration."""
        accounts = []
        for key in self._read_all():
            if key == integration:
                accounts.append("default")
            elif key.startswith(f"{integration}:"):
                accounts.append(key.removeprefix(f"{integration}:"))
        return accounts


def _get_token_store() -> TokenStore:
    return TokenStore(get_settings().token_file)


def _create_flow(integration: str) -> Flow:
    settings = get_settings()
    if not settings.client_secret_file.exists():
        raise FileNotFoundError(
            f"OAuth client secret file not found at {settings.client_secret_file}. "
            "Download it from Google Cloud Console."
        )
    return Flow.from_client_secrets_file(
        str(settings.client_secret_file),
        scopes=INTEGRATION_SCOPES[integration],
        redirect_uri=_redirect_uri(integration),
    )


def _get_credentials(integration: str, account: str = "default") -> Credentials:
    """Load credentials from token store. Refreshes if expired, raises if missing."""
    store = _get_token_store()
    key = _token_key(integration, account)
    token_data = store.get(key)

    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, INTEGRATION_SCOPES[integration])
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            store.save(key, json.loads(creds.to_json()))
            return creds

    label = f" (account={account})" if account != "default" else ""
    raise RuntimeError(
        f"{integration} not authenticated{label}. Visit /auth/{integration}/setup?account={account} to connect."
    )


def get_gmail_credentials(account: str = "default") -> Credentials:
    return _get_credentials("gmail", account)


def get_drive_credentials(account: str = "default") -> Credentials:
    return _get_credentials("drive", account)


# --- Auth router ---

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{integration}/setup")
def auth_setup(integration: str, account: str = "default"):
    """Redirect to Google OAuth consent screen. Use ?account=name for multiple accounts."""
    if integration not in SUPPORTED_INTEGRATIONS:
        return StatusResponse(integration=integration, authenticated=False, message=f"Unknown integration: {integration}")
    flow = _create_flow(integration)
    # Encode integration:account in state so callback knows where to store the token
    state = f"{integration}:{account}"
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return RedirectResponse(auth_url)


@router.get("/{integration}/callback")
def auth_callback(integration: str, code: str, state: str = ""):
    """Handle OAuth callback from Google, exchange code for tokens."""
    # Parse state to get integration and account
    if ":" in state:
        _, account = state.split(":", 1)
    else:
        account = "default"
    if integration not in SUPPORTED_INTEGRATIONS:
        return StatusResponse(integration=integration, authenticated=False, message=f"Unknown integration: {integration}")
    flow = _create_flow(integration)
    flow.fetch_token(code=code)
    creds = flow.credentials
    store = _get_token_store()
    store.save(_token_key(integration, account), json.loads(creds.to_json()))
    return StatusResponse(
        integration=integration,
        authenticated=True,
        message=f"{integration} account '{account}' authenticated successfully. You can close this tab.",
    )


@router.get("/{integration}/accounts")
def list_accounts(integration: str) -> dict:
    """List all authenticated accounts for an integration."""
    store = _get_token_store()
    return {"accounts": store.list_accounts(integration)}


@router.get("/{integration}/status")
def auth_status(integration: str, account: str = "default") -> StatusResponse:
    """Check whether an integration has a valid token."""
    if integration not in SUPPORTED_INTEGRATIONS:
        return StatusResponse(integration=integration, authenticated=False, message=f"Unknown integration: {integration}")
    store = _get_token_store()
    key = _token_key(integration, account)
    valid = store.has_valid_token(key)
    label = f" (account={account})" if account != "default" else ""
    return StatusResponse(
        integration=integration,
        authenticated=valid,
        message=f"Authenticated{label}" if valid else f"Not authenticated{label} — visit /auth/{integration}/setup?account={account}",
    )
