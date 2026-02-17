import json
from pathlib import Path

from fastapi import APIRouter
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from brokenclaw.config import get_settings
from brokenclaw.models.common import StatusResponse

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class TokenStore:
    """Reads/writes OAuth tokens to a local JSON file, keyed by integration name."""

    def __init__(self, path: Path):
        self.path = path

    def _read_all(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def get(self, integration: str) -> dict | None:
        return self._read_all().get(integration)

    def save(self, integration: str, token_data: dict) -> None:
        all_tokens = self._read_all()
        all_tokens[integration] = token_data
        self.path.write_text(json.dumps(all_tokens, indent=2))

    def has_valid_token(self, integration: str) -> bool:
        token_data = self.get(integration)
        if not token_data:
            return False
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        return creds.valid or (creds.expired and creds.refresh_token)


def _get_token_store() -> TokenStore:
    return TokenStore(get_settings().token_file)


def get_gmail_credentials() -> Credentials:
    """Load Gmail credentials from token store. Refreshes if expired, runs OAuth flow if missing."""
    store = _get_token_store()
    token_data = store.get("gmail")

    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            store.save("gmail", json.loads(creds.to_json()))
            return creds

    # No valid token — run browser OAuth flow
    settings = get_settings()
    if not settings.client_secret_file.exists():
        raise FileNotFoundError(
            f"OAuth client secret file not found at {settings.client_secret_file}. "
            "Download it from Google Cloud Console."
        )
    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.client_secret_file), GMAIL_SCOPES
    )
    creds = flow.run_local_server(port=0)
    store.save("gmail", json.loads(creds.to_json()))
    return creds


# --- Auth router ---

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{integration}/setup")
def auth_setup(integration: str) -> StatusResponse:
    """Trigger OAuth flow for an integration. Opens browser for consent."""
    if integration != "gmail":
        return StatusResponse(
            integration=integration,
            authenticated=False,
            message=f"Unknown integration: {integration}",
        )
    get_gmail_credentials()
    return StatusResponse(
        integration="gmail", authenticated=True, message="Gmail authenticated successfully"
    )


@router.get("/{integration}/status")
def auth_status(integration: str) -> StatusResponse:
    """Check whether an integration has a valid token."""
    if integration != "gmail":
        return StatusResponse(
            integration=integration,
            authenticated=False,
            message=f"Unknown integration: {integration}",
        )
    store = _get_token_store()
    valid = store.has_valid_token("gmail")
    return StatusResponse(
        integration="gmail",
        authenticated=valid,
        message="Authenticated" if valid else "Not authenticated — visit /auth/gmail/setup",
    )
