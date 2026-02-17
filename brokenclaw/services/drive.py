import io

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from brokenclaw.auth import get_drive_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.drive import DriveFile, FileContentResponse

FIELDS = "id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink"


def _get_drive_service(account: str = "default"):
    try:
        creds = get_drive_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Drive credentials: {e}. Visit /auth/drive/setup?account={account}."
        ) from e
    return build("drive", "v3", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Drive API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Drive credentials expired or revoked. Visit /auth/drive/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Drive API error: {e}") from e


def _parse_file(f: dict) -> DriveFile:
    return DriveFile(
        id=f["id"],
        name=f.get("name", ""),
        mime_type=f.get("mimeType", ""),
        size=f.get("size"),
        created_time=f.get("createdTime"),
        modified_time=f.get("modifiedTime"),
        parents=f.get("parents"),
        web_view_link=f.get("webViewLink"),
    )


def list_files(max_results: int = 20, account: str = "default") -> list[DriveFile]:
    """List recent files in Drive."""
    service = _get_drive_service(account)
    try:
        results = service.files().list(
            pageSize=max_results,
            fields=f"files({FIELDS})",
            orderBy="modifiedTime desc",
        ).execute()
        return [_parse_file(f) for f in results.get("files", [])]
    except HttpError as e:
        _handle_api_error(e)


def search_files(query: str, max_results: int = 20, account: str = "default") -> list[DriveFile]:
    """Search files using Drive query syntax (e.g. name contains 'report')."""
    service = _get_drive_service(account)
    try:
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields=f"files({FIELDS})",
            orderBy="modifiedTime desc",
        ).execute()
        return [_parse_file(f) for f in results.get("files", [])]
    except HttpError as e:
        _handle_api_error(e)


def get_file(file_id: str, account: str = "default") -> DriveFile:
    """Get file metadata by ID."""
    service = _get_drive_service(account)
    try:
        f = service.files().get(fileId=file_id, fields=FIELDS).execute()
        return _parse_file(f)
    except HttpError as e:
        _handle_api_error(e)


def get_file_content(file_id: str, account: str = "default") -> FileContentResponse:
    """Download text content of a file. Works for Google Docs (exported as plain text) and plain text files."""
    service = _get_drive_service(account)
    try:
        meta = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
        mime = meta.get("mimeType", "")

        # Google Docs/Sheets/Slides need to be exported
        export_map = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
            "application/vnd.google-apps.presentation": "text/plain",
        }

        if mime in export_map:
            content = service.files().export(fileId=file_id, mimeType=export_map[mime]).execute()
            text = content.decode("utf-8") if isinstance(content, bytes) else content
        else:
            content = service.files().get_media(fileId=file_id).execute()
            text = content.decode("utf-8") if isinstance(content, bytes) else str(content)

        return FileContentResponse(id=meta["id"], name=meta["name"], mime_type=mime, content=text)
    except HttpError as e:
        _handle_api_error(e)


def create_file(name: str, content: str, mime_type: str = "text/plain", parent_folder_id: str | None = None, account: str = "default") -> DriveFile:
    """Create a new file in Drive."""
    service = _get_drive_service(account)
    metadata: dict = {"name": name}
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]

    media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype=mime_type)
    try:
        f = service.files().create(body=metadata, media_body=media, fields=FIELDS).execute()
        return _parse_file(f)
    except HttpError as e:
        _handle_api_error(e)


def create_folder(name: str, parent_folder_id: str | None = None, account: str = "default") -> DriveFile:
    """Create a new folder in Drive."""
    service = _get_drive_service(account)
    metadata: dict = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]
    try:
        f = service.files().create(body=metadata, fields=FIELDS).execute()
        return _parse_file(f)
    except HttpError as e:
        _handle_api_error(e)
