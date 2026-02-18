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
from brokenclaw.services import maps as maps_service
from brokenclaw.services import youtube as youtube_service
from brokenclaw.services import calendar as calendar_service
from brokenclaw.services import news as news_service
from brokenclaw.services import github as github_service
from brokenclaw.services import wolfram as wolfram_service
from brokenclaw.services import canvas as canvas_service

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


# --- Maps tools ---

@mcp.tool
def maps_geocode(address: str) -> dict:
    """Convert an address or place name to geographic coordinates (lat/lng).
    Example: 'Empire State Building, New York' or '1600 Amphitheatre Parkway, Mountain View, CA'."""
    try:
        results = maps_service.geocode(address)
        return {"results": [r.model_dump() for r in results], "count": len(results)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_reverse_geocode(lat: float, lng: float) -> dict:
    """Convert geographic coordinates to a human-readable address."""
    try:
        results = maps_service.reverse_geocode(lat, lng)
        return {"results": [r.model_dump() for r in results], "count": len(results)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_directions(origin: str, destination: str, mode: str = "driving") -> dict:
    """Get directions between two places. Returns routes with step-by-step instructions, distance, and duration.
    Mode: 'driving', 'walking', 'bicycling', or 'transit'."""
    try:
        routes = maps_service.directions(origin, destination, mode)
        return {"routes": [r.model_dump() for r in routes], "count": len(routes)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_search_places(query: str, max_results: int = 10) -> dict:
    """Search for places by text query. Example: 'coffee shops near Times Square' or 'best pizza in Chicago'.
    Returns place names, addresses, ratings, and place IDs for further detail lookup."""
    try:
        results = maps_service.search_places(query, max_results)
        return {"places": [r.model_dump() for r in results], "count": len(results)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_place_details(place_id: str) -> dict:
    """Get detailed information about a place by its place ID (from maps_search_places or maps_geocode).
    Returns name, address, phone, website, rating, and Google Maps URL."""
    try:
        return maps_service.get_place_details(place_id).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_distance_matrix(origins: list[str], destinations: list[str], mode: str = "driving") -> dict:
    """Calculate travel distance and time between multiple origins and destinations.
    Mode: 'driving', 'walking', 'bicycling', or 'transit'.
    Example: origins=['New York'], destinations=['Boston', 'Philadelphia']."""
    try:
        entries = maps_service.distance_matrix(origins, destinations, mode)
        return {"entries": [e.model_dump() for e in entries], "count": len(entries)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_current_weather(lat: float, lng: float, units: str = "IMPERIAL") -> dict:
    """Get current weather conditions at a location (by latitude/longitude).
    Use maps_geocode first to convert an address to coordinates.
    Units: 'IMPERIAL' (Fahrenheit, mph) or 'METRIC' (Celsius, km/h)."""
    try:
        return maps_service.get_current_weather(lat, lng, units).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_daily_forecast(lat: float, lng: float, days: int = 5, units: str = "IMPERIAL") -> dict:
    """Get daily weather forecast for up to 10 days at a location.
    Use maps_geocode first to convert an address to coordinates.
    Units: 'IMPERIAL' or 'METRIC'."""
    try:
        forecasts = maps_service.get_daily_forecast(lat, lng, days, units)
        return {"forecasts": [f.model_dump() for f in forecasts], "days": len(forecasts)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def maps_timezone(lat: float, lng: float) -> dict:
    """Get timezone information for a location. Returns timezone ID (e.g. 'America/New_York'),
    name, and UTC offsets. Use maps_geocode first to convert an address to coordinates."""
    try:
        return maps_service.get_timezone(lat, lng).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- YouTube tools ---

@mcp.tool
def youtube_search(query: str, max_results: int = 10, account: str = "default") -> dict:
    """Search YouTube for videos. Returns a list of videos with title, description, channel, and URL.
    Use account parameter to specify which YouTube account."""
    try:
        videos = youtube_service.search_videos(query, max_results, account=account)
        return {"videos": [v.model_dump() for v in videos], "count": len(videos)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def youtube_get_video(video_id: str, account: str = "default") -> dict:
    """Get detailed information about a YouTube video by its ID.
    Returns title, description, tags, duration, view/like/comment counts, and URL."""
    try:
        return youtube_service.get_video(video_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def youtube_get_channel(channel_id: str, account: str = "default") -> dict:
    """Get YouTube channel information by channel ID.
    Returns title, description, subscriber/video/view counts, and URL."""
    try:
        return youtube_service.get_channel(channel_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def youtube_list_playlists(channel_id: str | None = None, max_results: int = 25, account: str = "default") -> dict:
    """List YouTube playlists. If channel_id is provided, lists that channel's playlists.
    If omitted, lists the authenticated user's own playlists."""
    try:
        playlists = youtube_service.list_playlists(channel_id, max_results, account=account)
        return {"playlists": [p.model_dump() for p in playlists], "count": len(playlists)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def youtube_list_playlist_items(playlist_id: str, max_results: int = 50, account: str = "default") -> dict:
    """List videos in a YouTube playlist. Returns video titles, descriptions, positions, and URLs."""
    try:
        items = youtube_service.list_playlist_items(playlist_id, max_results, account=account)
        return {"items": [i.model_dump() for i in items], "count": len(items)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Calendar tools ---

@mcp.tool
def calendar_list_calendars(max_results: int = 50, account: str = "default") -> dict:
    """List all Google Calendars the user has access to. Returns calendar names, IDs, and time zones.
    The primary calendar ID is typically the user's email address."""
    try:
        calendars = calendar_service.list_calendars(max_results, account=account)
        return {"calendars": [c.model_dump() for c in calendars], "count": len(calendars)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def calendar_list_events(
    calendar_id: str = "primary",
    max_results: int = 25,
    time_min: str | None = None,
    time_max: str | None = None,
    query: str | None = None,
    account: str = "default",
) -> dict:
    """List upcoming calendar events. Defaults to events from now onward.
    Use 'primary' for the user's main calendar. time_min/time_max in RFC 3339 format.
    Use query to search event titles/descriptions (e.g. 'meeting')."""
    try:
        events = calendar_service.list_events(calendar_id, max_results, time_min, time_max, query, account=account)
        return {"events": [e.model_dump() for e in events], "count": len(events)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def calendar_get_event(event_id: str, calendar_id: str = "primary", account: str = "default") -> dict:
    """Get a specific calendar event by its event ID. Returns full event details including attendees."""
    try:
        return calendar_service.get_event(calendar_id, event_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def calendar_create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
    time_zone: str | None = None,
    attendees: list[str] | None = None,
    account: str = "default",
) -> dict:
    """Create a new calendar event. start_datetime and end_datetime in RFC 3339 format
    (e.g. '2025-03-01T09:00:00-05:00'). Optionally provide time_zone (e.g. 'America/New_York'),
    description, location, and attendee email addresses."""
    try:
        return calendar_service.create_event(
            summary, start_datetime, end_datetime, calendar_id,
            description, location, time_zone, attendees, account=account,
        ).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def calendar_update_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    description: str | None = None,
    location: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    time_zone: str | None = None,
    account: str = "default",
) -> dict:
    """Update an existing calendar event. Only provided fields are changed.
    Use calendar_list_events to find the event_id first."""
    try:
        return calendar_service.update_event(
            calendar_id, event_id, summary, description, location,
            start_datetime, end_datetime, time_zone, account=account,
        ).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def calendar_delete_event(event_id: str, calendar_id: str = "primary", account: str = "default") -> dict:
    """Delete a calendar event by its event ID."""
    try:
        calendar_service.delete_event(calendar_id, event_id, account=account)
        return {"status": "deleted", "event_id": event_id}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def calendar_quick_add(text: str, calendar_id: str = "primary", account: str = "default") -> dict:
    """Create a calendar event from natural language text. Google parses the text to extract
    event details. Examples: 'Meeting with Bob tomorrow at 3pm', 'Lunch at noon on Friday at Cafe Roma'."""
    try:
        return calendar_service.quick_add_event(text, calendar_id, account=account).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- News tools ---

@mcp.tool
def news_top_headlines(
    country: str | None = "us",
    category: str | None = None,
    query: str | None = None,
    page_size: int = 20,
) -> dict:
    """Get top news headlines. Filter by country (2-letter code, e.g. 'us', 'gb') and/or category
    (business, entertainment, general, health, science, sports, technology).
    Optionally search within headlines with a query."""
    try:
        return news_service.top_headlines(country, category, query, page_size).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def news_search(
    query: str,
    language: str = "en",
    sort_by: str = "publishedAt",
    from_date: str | None = None,
    to_date: str | None = None,
    domains: str | None = None,
    page_size: int = 20,
) -> dict:
    """Search all news articles from 150,000+ sources. Sort by 'relevancy', 'popularity', or 'publishedAt'.
    Filter by date range (ISO format, e.g. '2025-03-01') and specific domains (e.g. 'bbc.co.uk,cnn.com').
    Supports operators: AND, OR, NOT, quotes for exact match."""
    try:
        return news_service.search_news(query, language, sort_by, from_date, to_date, domains, page_size).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- GitHub tools ---

@mcp.tool
def github_list_repos(sort: str = "updated", per_page: int = 30) -> dict:
    """List your GitHub repositories, sorted by most recently updated.
    Sort options: 'updated', 'created', 'pushed', 'full_name'."""
    try:
        repos = github_service.list_repos(sort, per_page)
        return {"repos": [r.model_dump() for r in repos], "count": len(repos)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_get_repo(owner: str, repo: str) -> dict:
    """Get detailed information about a GitHub repository.
    Example: owner='octocat', repo='hello-world'."""
    try:
        return github_service.get_repo(owner, repo).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_search_repos(query: str, sort: str = "stars", per_page: int = 20) -> dict:
    """Search GitHub repositories. Supports qualifiers like 'language:python stars:>100'.
    Sort options: 'stars', 'forks', 'updated'."""
    try:
        return github_service.search_repos(query, sort, per_page).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    per_page: int = 30,
) -> dict:
    """List issues for a GitHub repository (excludes pull requests).
    Filter by state ('open', 'closed', 'all') and labels (comma-separated)."""
    try:
        issues = github_service.list_issues(owner, repo, state, labels, per_page)
        return {"issues": [i.model_dump() for i in issues], "count": len(issues)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_get_issue(owner: str, repo: str, issue_number: int) -> dict:
    """Get a specific GitHub issue by number. Returns full details including body text."""
    try:
        return github_service.get_issue(owner, repo, issue_number).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Create a new issue in a GitHub repository.
    Optionally add labels and assignees (GitHub usernames)."""
    try:
        return github_service.create_issue(owner, repo, title, body, labels, assignees).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> dict:
    """List pull requests for a GitHub repository.
    Filter by state: 'open', 'closed', 'all'."""
    try:
        prs = github_service.list_pull_requests(owner, repo, state, per_page)
        return {"pull_requests": [pr.model_dump() for pr in prs], "count": len(prs)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_get_pull_request(owner: str, repo: str, pr_number: int) -> dict:
    """Get detailed info about a specific pull request, including diff stats and merge status."""
    try:
        return github_service.get_pull_request(owner, repo, pr_number).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def github_notifications(
    all_notifications: bool = False,
    participating: bool = False,
    per_page: int = 30,
) -> dict:
    """List your GitHub notifications. By default shows only unread.
    Set all_notifications=True for read+unread, participating=True for only direct involvement."""
    try:
        notifs = github_service.list_notifications(all_notifications, participating, per_page)
        return {"notifications": [n.model_dump() for n in notifs], "count": len(notifs)}
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)



# --- Wolfram Alpha tools ---

@mcp.tool
def wolfram_query(input: str, units: str = "nonmetric") -> dict:
    """Ask Wolfram Alpha a question and get detailed structured results with multiple pods.
    Great for math, science, conversions, statistics, geography, and factual queries.
    Units: 'nonmetric' (US customary) or 'metric'. Examples: 'integrate x^2 dx',
    'population of France', 'distance from Earth to Mars', '150 USD to EUR'."""
    try:
        return wolfram_service.query(input, units).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def wolfram_short_answer(input: str, units: str = "imperial") -> dict:
    """Get a quick one-line answer from Wolfram Alpha. Faster than full query but less detail.
    Good for simple factual questions. Examples: 'How tall is the Eiffel Tower?',
    'What is the square root of 144?', 'When is the next solar eclipse?'."""
    try:
        return wolfram_service.short_answer(input, units).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)



# --- Canvas tools ---

@mcp.tool
def canvas_upcoming(days: int = 14) -> dict:
    """Get upcoming Canvas LMS assignments and events within the next N days (default 14).
    Returns assignment names, due dates, course names, and Canvas URLs.
    Great for checking what's due soon."""
    try:
        return canvas_service.get_upcoming(days).model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


@mcp.tool
def canvas_all_events() -> dict:
    """Get all Canvas LMS assignments and events from the calendar feed.
    Includes past and future items, sorted chronologically."""
    try:
        return canvas_service.get_all_events().model_dump()
    except (AuthenticationError, IntegrationError, RateLimitError) as e:
        return _handle_mcp_error(e)


# --- Status tool ---

@mcp.tool
def brokenclaw_status() -> dict:
    """Check which integrations are authenticated and ready to use.
    Shows all authenticated accounts per integration and Maps API key status."""
    from brokenclaw.config import get_settings
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
    maps_key = get_settings().google_maps_api_key
    integrations["maps"] = {
        "authenticated_accounts": ["api_key"] if maps_key else [],
        "message": "API key configured" if maps_key else "No API key — set GOOGLE_MAPS_API_KEY in .env",
    }
    news_key = get_settings().news_api_key
    integrations["news"] = {
        "authenticated_accounts": ["api_key"] if news_key else [],
        "message": "API key configured" if news_key else "No API key — get one at newsapi.org and set NEWS_API_KEY in .env",
    }
    github_token = get_settings().github_token
    integrations["github"] = {
        "authenticated_accounts": ["token"] if github_token else [],
        "message": "Token configured" if github_token else "No token — create a PAT at github.com/settings/tokens and set GITHUB_TOKEN in .env",
    }
    wolfram_id = get_settings().wolfram_app_id
    integrations["wolfram"] = {
        "authenticated_accounts": ["app_id"] if wolfram_id else [],
        "message": "AppID configured" if wolfram_id else "No AppID — get one at developer.wolframalpha.com and set WOLFRAM_APP_ID in .env",
    }
    canvas_url = get_settings().canvas_feed_url
    integrations["canvas"] = {
        "authenticated_accounts": ["ical_feed"] if canvas_url else [],
        "message": "iCal feed URL configured" if canvas_url else "No feed URL — set CANVAS_FEED_URL in .env (get from Canvas > Calendar > Calendar Feed)",
    }
    return {"integrations": integrations}
