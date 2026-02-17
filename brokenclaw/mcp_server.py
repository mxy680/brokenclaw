from fastmcp import FastMCP

from brokenclaw.auth import SUPPORTED_INTEGRATIONS, _get_token_store
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.services import docs as docs_service
from brokenclaw.services import drive as drive_service
from brokenclaw.services import gmail as gmail_service
from brokenclaw.services import sheets as sheets_service
from brokenclaw.services import slides as slides_service
from brokenclaw.services import tasks as tasks_service
from brokenclaw.services import forms as forms_service

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


# --- Docs tools ---

@mcp.tool
def docs_get_document(document_id: str, account: str = "default") -> dict:
    """Get Google Doc metadata: title, ID, and URL.
    You need the document ID from the URL: docs.google.com/document/d/{DOCUMENT_ID}/edit"""
    try:
        return docs_service.get_document(document_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def docs_read_document(document_id: str, account: str = "default") -> dict:
    """Read the full text content of a Google Doc. Returns the document title and extracted body text.
    Use this to read the contents of a document."""
    try:
        return docs_service.get_document_content(document_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def docs_create_document(title: str, account: str = "default") -> dict:
    """Create a new empty Google Doc with the given title.
    Returns the new document ID, title, and URL."""
    try:
        return docs_service.create_document(title, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def docs_insert_text(document_id: str, text: str, index: int = 1, account: str = "default") -> dict:
    """Insert text into a Google Doc at the specified position.
    Index 1 = start of document body (default). The index refers to the character offset in the document."""
    try:
        return docs_service.insert_text(document_id, text, index, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def docs_replace_text(document_id: str, find: str, replace_with: str, match_case: bool = True, account: str = "default") -> dict:
    """Find and replace text in a Google Doc. Replaces all occurrences of 'find' with 'replace_with'.
    Set match_case=False for case-insensitive matching."""
    try:
        return docs_service.replace_text(document_id, find, replace_with, match_case, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Slides tools ---

@mcp.tool
def slides_get_presentation(presentation_id: str, account: str = "default") -> dict:
    """Get Google Slides presentation metadata: title, slide count, and URL.
    You need the presentation ID from the URL: docs.google.com/presentation/d/{PRESENTATION_ID}/edit"""
    try:
        return slides_service.get_presentation(presentation_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def slides_read_presentation(presentation_id: str, account: str = "default") -> dict:
    """Read the text content from all slides in a Google Slides presentation.
    Returns the title and a list of text strings, one per slide."""
    try:
        return slides_service.get_presentation_content(presentation_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def slides_create_presentation(title: str, account: str = "default") -> dict:
    """Create a new Google Slides presentation with the given title.
    Returns the new presentation ID, title, slide count, and URL."""
    try:
        return slides_service.create_presentation(title, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def slides_add_slide(presentation_id: str, layout: str = "BLANK", account: str = "default") -> dict:
    """Add a new slide to a presentation. Layout options include BLANK, TITLE, TITLE_AND_BODY,
    TITLE_AND_TWO_COLUMNS, TITLE_ONLY, SECTION_HEADER, etc. Defaults to BLANK."""
    try:
        return slides_service.add_slide(presentation_id, layout, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def slides_replace_text(presentation_id: str, find: str, replace_with: str, match_case: bool = True, account: str = "default") -> dict:
    """Find and replace text across all slides in a presentation. Replaces all occurrences of 'find' with 'replace_with'.
    Set match_case=False for case-insensitive matching."""
    try:
        return slides_service.replace_text(presentation_id, find, replace_with, match_case, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Tasks tools ---

@mcp.tool
def tasks_list_task_lists(max_results: int = 20, account: str = "default") -> dict:
    """List all Google Tasks lists for the user. Returns task list names and IDs.
    Every user has at least one default task list."""
    try:
        lists = tasks_service.list_task_lists(max_results, account=account)
        return {"task_lists": [tl.model_dump() for tl in lists], "count": len(lists)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def tasks_create_task_list(title: str, account: str = "default") -> dict:
    """Create a new Google Tasks list with the given title."""
    try:
        return tasks_service.create_task_list(title, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def tasks_list_tasks(tasklist_id: str = "@default", max_results: int = 100, show_completed: bool = True, account: str = "default") -> dict:
    """List tasks in a Google Tasks list. Use '@default' for the user's default task list.
    Set show_completed=False to hide completed tasks."""
    try:
        tasks = tasks_service.list_tasks(tasklist_id, max_results, show_completed, account=account)
        return {"tasks": [t.model_dump() for t in tasks], "count": len(tasks)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def tasks_create_task(title: str, tasklist_id: str = "@default", notes: str | None = None, due: str | None = None, account: str = "default") -> dict:
    """Create a new task. Use '@default' for the default task list.
    Optionally provide notes and a due date (RFC 3339 format, e.g. '2025-03-01T00:00:00Z')."""
    try:
        return tasks_service.create_task(tasklist_id, title, notes, due, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def tasks_update_task(tasklist_id: str, task_id: str, title: str | None = None, notes: str | None = None, status: str | None = None, due: str | None = None, account: str = "default") -> dict:
    """Update an existing task. Only provided fields are changed.
    Status must be 'needsAction' or 'completed'. Due date in RFC 3339 format."""
    try:
        return tasks_service.update_task(tasklist_id, task_id, title, notes, status, due, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def tasks_complete_task(tasklist_id: str, task_id: str, account: str = "default") -> dict:
    """Mark a task as completed."""
    try:
        return tasks_service.complete_task(tasklist_id, task_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def tasks_delete_task(tasklist_id: str, task_id: str, account: str = "default") -> dict:
    """Delete a task from a task list."""
    try:
        tasks_service.delete_task(tasklist_id, task_id, account=account)
        return {"status": "deleted", "task_id": task_id}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Forms tools ---

@mcp.tool
def forms_get_form(form_id: str, account: str = "default") -> dict:
    """Get Google Form metadata: title, description, and responder URL.
    You need the form ID from the URL: docs.google.com/forms/d/{FORM_ID}/edit"""
    try:
        return forms_service.get_form(form_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def forms_get_form_detail(form_id: str, account: str = "default") -> dict:
    """Get a Google Form with all its questions. Returns form metadata plus a list of questions
    with their types (TEXT, PARAGRAPH, RADIO, CHECKBOX, DROP_DOWN, SCALE, etc.)."""
    try:
        return forms_service.get_form_detail(form_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def forms_create_form(title: str, account: str = "default") -> dict:
    """Create a new empty Google Form with the given title.
    Returns the form ID, title, responder URI (share this for people to fill out), and edit URL."""
    try:
        return forms_service.create_form(title, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def forms_add_question(form_id: str, title: str, question_type: str = "TEXT", options: list[str] | None = None, required: bool = False, account: str = "default") -> dict:
    """Add a question to a Google Form. Types: TEXT (short answer), PARAGRAPH (long answer),
    RADIO (multiple choice), CHECKBOX (checkboxes), DROP_DOWN (dropdown).
    For RADIO/CHECKBOX/DROP_DOWN, provide options as a list of strings."""
    try:
        return forms_service.add_question(form_id, title, question_type, options, required, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def forms_list_responses(form_id: str, max_results: int = 100, account: str = "default") -> dict:
    """List all responses submitted to a Google Form. Returns response IDs, timestamps, and answers."""
    try:
        responses = forms_service.list_responses(form_id, max_results, account=account)
        return {"responses": [r.model_dump() for r in responses], "count": len(responses)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def forms_get_response(form_id: str, response_id: str, account: str = "default") -> dict:
    """Get a single form response by its response ID. Returns the full answers for that submission."""
    try:
        return forms_service.get_response(form_id, response_id, account=account).model_dump()
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
