from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_sheets_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.sheets import (
    ReadRangeResponse,
    SpreadsheetInfo,
    WriteRangeResponse,
)


def _get_sheets_service(account: str = "default"):
    try:
        creds = get_sheets_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Sheets credentials: {e}. Visit /auth/sheets/setup?account={account}."
        ) from e
    return build("sheets", "v4", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Sheets API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Sheets credentials expired or revoked. Visit /auth/sheets/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Sheets API error: {e}") from e


def get_spreadsheet(spreadsheet_id: str, account: str = "default") -> SpreadsheetInfo:
    """Get spreadsheet metadata: title, sheet names, URL."""
    service = _get_sheets_service(account)
    try:
        result = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute(num_retries=3)
        sheets = [s["properties"]["title"] for s in result.get("sheets", [])]
        return SpreadsheetInfo(
            id=result["spreadsheetId"],
            title=result["properties"]["title"],
            sheets=sheets,
            url=result.get("spreadsheetUrl", ""),
        )
    except HttpError as e:
        _handle_api_error(e)


def read_range(spreadsheet_id: str, range: str, account: str = "default") -> ReadRangeResponse:
    """Read a range of cells (e.g. 'Sheet1!A1:D10')."""
    service = _get_sheets_service(account)
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range
        ).execute(num_retries=3)
        return ReadRangeResponse(
            spreadsheet_id=spreadsheet_id,
            range=result.get("range", range),
            values=result.get("values", []),
        )
    except HttpError as e:
        _handle_api_error(e)


def write_range(spreadsheet_id: str, range: str, values: list[list[str]], account: str = "default") -> WriteRangeResponse:
    """Write values to a range of cells."""
    service = _get_sheets_service(account)
    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute(num_retries=3)
        return WriteRangeResponse(
            spreadsheet_id=spreadsheet_id,
            updated_range=result.get("updatedRange", range),
            updated_rows=result.get("updatedRows", 0),
            updated_columns=result.get("updatedColumns", 0),
            updated_cells=result.get("updatedCells", 0),
        )
    except HttpError as e:
        _handle_api_error(e)


def append_rows(spreadsheet_id: str, range: str, values: list[list[str]], account: str = "default") -> WriteRangeResponse:
    """Append rows after the last row with data in the range."""
    service = _get_sheets_service(account)
    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute(num_retries=3)
        updates = result.get("updates", {})
        return WriteRangeResponse(
            spreadsheet_id=spreadsheet_id,
            updated_range=updates.get("updatedRange", range),
            updated_rows=updates.get("updatedRows", 0),
            updated_columns=updates.get("updatedColumns", 0),
            updated_cells=updates.get("updatedCells", 0),
        )
    except HttpError as e:
        _handle_api_error(e)


def create_spreadsheet(title: str, sheet_names: list[str] | None = None, account: str = "default") -> SpreadsheetInfo:
    """Create a new spreadsheet with optional sheet names."""
    service = _get_sheets_service(account)
    body: dict = {"properties": {"title": title}}
    if sheet_names:
        body["sheets"] = [{"properties": {"title": name}} for name in sheet_names]
    try:
        result = service.spreadsheets().create(body=body).execute(num_retries=3)
        sheets = [s["properties"]["title"] for s in result.get("sheets", [])]
        return SpreadsheetInfo(
            id=result["spreadsheetId"],
            title=result["properties"]["title"],
            sheets=sheets,
            url=result.get("spreadsheetUrl", ""),
        )
    except HttpError as e:
        _handle_api_error(e)
