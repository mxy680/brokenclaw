from fastmcp import FastMCP

from brokenclaw.auth import SUPPORTED_INTEGRATIONS, _get_token_store
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.services import drive as drive_service
from brokenclaw.services import gmail as gmail_service
from brokenclaw.services import sheets as sheets_service

mcp = FastMCP("Brokenclaw")


def _handle_mcp_error(e: Exception) -> dict:
    """Convert exceptions to agent-friendly error dicts."""
    if isinstance(e, AuthenticationError):
        return {"error": "auth_error", "message": str(e), "action": "Ask user to visit the setup URL shown in the message"}
    if isinstance(e, RateLimitError):
        return {"error": "rate_limit", "message": str(e), "action": "Wait a moment and retry"}
    if isinstance(e, IntegrationError):
        return {"error": "integration_error", "message": str(e)}
    return {"error": "unknown_error", "message": str(e)}


# --- Gmail tools ---

@mcp.tool
def gmail_inbox(max_results: int = 20, account: str = "default") -> dict:
    """Get recent inbox messages. Returns a list of email messages with subject, sender, date, and snippet.
    Use account parameter to specify which Gmail account (e.g. 'personal', 'work'). Defaults to 'default'."""
    try:
        messages = gmail_service.get_inbox(max_results, account=account)
        return {"messages": [m.model_dump() for m in messages], "count": len(messages)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def gmail_search(query: str, max_results: int = 20, account: str = "default") -> dict:
    """Search emails using Gmail query syntax (e.g. 'from:alice subject:meeting after:2024/01/01').
    Returns matching messages with subject, sender, date, and snippet.
    Use account parameter to specify which Gmail account."""
    try:
        messages = gmail_service.search_messages(query, max_results, account=account)
        return {"messages": [m.model_dump() for m in messages], "count": len(messages)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def gmail_get_message(message_id: str, account: str = "default") -> dict:
    """Get the full content of a specific email by its message ID.
    Use this after gmail_inbox or gmail_search to read the full body."""
    try:
        return gmail_service.get_message(message_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def gmail_send(to: str, subject: str, body: str, account: str = "default") -> dict:
    """Send a new email. Provide recipient address, subject line, and plain text body.
    Use account parameter to send from a specific Gmail account."""
    try:
        return gmail_service.send_message(to, subject, body, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def gmail_reply(message_id: str, body: str, account: str = "default") -> dict:
    """Reply to an existing email thread. Provide the message ID to reply to and the plain text reply body.
    Use account parameter to reply from a specific Gmail account."""
    try:
        return gmail_service.reply_to_message(message_id, body, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Drive tools ---

@mcp.tool
def drive_list_files(max_results: int = 20, account: str = "default") -> dict:
    """List recent files in Google Drive, ordered by last modified.
    Returns file name, ID, type, and last modified time."""
    try:
        files = drive_service.list_files(max_results, account=account)
        return {"files": [f.model_dump() for f in files], "count": len(files)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def drive_search(query: str, max_results: int = 20, account: str = "default") -> dict:
    """Search files in Google Drive using Drive query syntax.
    Examples: "name contains 'report'", "mimeType = 'application/pdf'", "modifiedTime > '2024-01-01'".
    See https://developers.google.com/drive/api/guides/search-files for full syntax."""
    try:
        files = drive_service.search_files(query, max_results, account=account)
        return {"files": [f.model_dump() for f in files], "count": len(files)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def drive_get_file(file_id: str, account: str = "default") -> dict:
    """Get metadata for a specific file by its ID (name, size, type, dates, link)."""
    try:
        return drive_service.get_file(file_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def drive_read_file(file_id: str, account: str = "default") -> dict:
    """Read the text content of a file. Works with Google Docs (exported as text), Sheets (exported as CSV), and plain text files.
    Use drive_list_files or drive_search first to find the file ID."""
    try:
        return drive_service.get_file_content(file_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def drive_create_file(name: str, content: str, mime_type: str = "text/plain", parent_folder_id: str | None = None, account: str = "default") -> dict:
    """Create a new file in Google Drive. Provide file name and text content.
    Optionally specify mime_type and parent_folder_id."""
    try:
        return drive_service.create_file(name, content, mime_type, parent_folder_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def drive_create_folder(name: str, parent_folder_id: str | None = None, account: str = "default") -> dict:
    """Create a new folder in Google Drive. Optionally place it inside an existing folder."""
    try:
        return drive_service.create_folder(name, parent_folder_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Sheets tools ---

@mcp.tool
def sheets_get_spreadsheet(spreadsheet_id: str, account: str = "default") -> dict:
    """Get spreadsheet metadata: title, list of sheet/tab names, and URL.
    You need the spreadsheet ID from the URL: docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"""
    try:
        return sheets_service.get_spreadsheet(spreadsheet_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def sheets_read_range(spreadsheet_id: str, range: str, account: str = "default") -> dict:
    """Read a range of cells from a spreadsheet. Range uses A1 notation, e.g. 'Sheet1!A1:D10' or just 'A1:D10'.
    Returns a 2D array of cell values."""
    try:
        return sheets_service.read_range(spreadsheet_id, range, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def sheets_write_range(spreadsheet_id: str, range: str, values: list[list[str]], account: str = "default") -> dict:
    """Write values to a range of cells. Range uses A1 notation. Values is a 2D array where each inner array is a row.
    Example: values=[["Name","Age"],["Alice","30"]] writes to two rows."""
    try:
        return sheets_service.write_range(spreadsheet_id, range, values, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def sheets_append_rows(spreadsheet_id: str, range: str, values: list[list[str]], account: str = "default") -> dict:
    """Append rows after the last row with data. Range specifies which sheet/area to append to (e.g. 'Sheet1!A:D').
    Values is a 2D array of rows to add."""
    try:
        return sheets_service.append_rows(spreadsheet_id, range, values, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def sheets_create_spreadsheet(title: str, sheet_names: list[str] | None = None, account: str = "default") -> dict:
    """Create a new Google Sheets spreadsheet. Optionally provide sheet/tab names.
    Returns the new spreadsheet ID, title, and URL."""
    try:
        return sheets_service.create_spreadsheet(title, sheet_names, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Status tool ---

@mcp.tool
def brokenclaw_status() -> dict:
    """Check which integrations are authenticated and ready to use.
    Shows all authenticated accounts per integration."""
    store = _get_token_store()
    integrations = {}
    for name in SUPPORTED_INTEGRATIONS:
        accounts = store.list_accounts(name)
        integrations[name] = {
            "authenticated_accounts": accounts,
            "message": (
                f"{len(accounts)} account(s) ready: {', '.join(accounts)}"
                if accounts
                else f"No accounts authenticated — user should visit /auth/{name}/setup"
            ),
        }
    return {"integrations": integrations}
