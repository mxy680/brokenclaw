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

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

REDIRECT_URI = "http://localhost:8000/auth/gmail/callback"


def _token_key(account: str) -> str:
    """Build token store key: 'gmail' for default, 'gmail:name' otherwise."""
    return "gmail" if account == "default" else f"gmail:{account}"


class TokenStore:
    """Reads/writes OAuth tokens to a local JSON file, keyed by integration name."""

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
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        return creds.valid or (creds.expired and creds.refresh_token)

    def list_gmail_accounts(self) -> list[str]:
        """Return all authenticated Gmail account names."""
        accounts = []
        for key in self._read_all():
            if key == "gmail":
                accounts.append("default")
            elif key.startswith("gmail:"):
                accounts.append(key.removeprefix("gmail:"))
        return accounts


def _get_token_store() -> TokenStore:
    return TokenStore(get_settings().token_file)


def _create_flow() -> Flow:
    settings = get_settings()
    if not settings.client_secret_file.exists():
        raise FileNotFoundError(
            f"OAuth client secret file not found at {settings.client_secret_file}. "
            "Download it from Google Cloud Console."
        )
    return Flow.from_client_secrets_file(
        str(settings.client_secret_file),
        scopes=GMAIL_SCOPES,
        redirect_uri=REDIRECT_URI,
    )


def get_gmail_credentials(account: str = "default") -> Credentials:
    """Load Gmail credentials from token store. Refreshes if expired, raises if missing."""
    store = _get_token_store()
    key = _token_key(account)
    token_data = store.get(key)

    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            store.save(key, json.loads(creds.to_json()))
            return creds

    label = f" (account={account})" if account != "default" else ""
    raise RuntimeError(
        f"Gmail not authenticated{label}. Visit /auth/gmail/setup?account={account} to connect."
    )


# --- Auth router ---

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/gmail/setup")
def gmail_auth_setup(account: str = "default"):
    """Redirect to Google OAuth consent screen. Use ?account=name for multiple accounts."""
    flow = _create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=account,  # pass account name through OAuth state
    )
    return RedirectResponse(auth_url)


@router.get("/gmail/callback")
def gmail_auth_callback(code: str, state: str = "default"):
    """Handle OAuth callback from Google, exchange code for tokens."""
    account = state
    flow = _create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    store = _get_token_store()
    store.save(_token_key(account), json.loads(creds.to_json()))
    return StatusResponse(
        integration="gmail",
        authenticated=True,
        message=f"Gmail account '{account}' authenticated successfully. You can close this tab.",
    )


@router.get("/gmail/accounts")
def gmail_accounts() -> dict:
    """List all authenticated Gmail accounts."""
    store = _get_token_store()
    return {"accounts": store.list_gmail_accounts()}


@router.get("/{integration}/status")
def auth_status(integration: str, account: str = "default") -> StatusResponse:
    """Check whether an integration has a valid token."""
    if integration != "gmail":
        return StatusResponse(
            integration=integration,
            authenticated=False,
            message=f"Unknown integration: {integration}",
        )
    store = _get_token_store()
    key = _token_key(account)
    valid = store.has_valid_token(key)
    label = f" (account={account})" if account != "default" else ""
    return StatusResponse(
        integration="gmail",
        authenticated=valid,
        message=f"Authenticated{label}" if valid else f"Not authenticated{label} — visit /auth/gmail/setup?account={account}",
    )
