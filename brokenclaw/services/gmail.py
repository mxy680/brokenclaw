import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_gmail_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.gmail import GmailAttachment, GmailMessage


def _get_gmail_service(account: str = "default"):
    try:
        creds = get_gmail_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Gmail credentials: {e}. Visit /auth/gmail/setup?account={account}."
        ) from e
    return build("gmail", "v1", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Gmail API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Gmail credentials expired or revoked. Visit /auth/gmail/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Gmail API error: {e}") from e


def _parse_message(msg: dict) -> GmailMessage:
    """Extract a GmailMessage from the Gmail API message resource."""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    body = _extract_body(msg["payload"])
    attachments = _extract_attachments(msg["payload"])
    return GmailMessage(
        id=msg["id"],
        thread_id=msg["threadId"],
        subject=headers.get("subject", ""),
        from_addr=headers.get("from", ""),
        to_addr=headers.get("to", ""),
        date=headers.get("date", ""),
        snippet=msg.get("snippet", ""),
        body=body,
        attachments=attachments,
    )


def _extract_attachments(payload: dict) -> list[GmailAttachment]:
    """Recursively extract attachment metadata from message payload."""
    attachments = []
    filename = payload.get("filename")
    if filename:
        body = payload.get("body", {})
        attachments.append(GmailAttachment(
            filename=filename,
            mime_type=payload.get("mimeType"),
            size=body.get("size"),
            attachment_id=body.get("attachmentId"),
        ))
    for part in payload.get("parts", []):
        attachments.extend(_extract_attachments(part))
    return attachments


def _extract_body(payload: dict) -> str | None:
    """Recursively extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text
    return None


def get_inbox(max_results: int = 20, account: str = "default") -> list[GmailMessage]:
    """Get recent inbox messages."""
    service = _get_gmail_service(account)
    try:
        results = service.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=max_results
        ).execute(num_retries=3)
        messages = []
        for msg_ref in results.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute(num_retries=3)
            messages.append(_parse_message(msg))
        return messages
    except HttpError as e:
        _handle_api_error(e)


def search_messages(query: str, max_results: int = 20, account: str = "default") -> list[GmailMessage]:
    """Search messages using Gmail query syntax."""
    service = _get_gmail_service(account)
    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute(num_retries=3)
        messages = []
        for msg_ref in results.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute(num_retries=3)
            messages.append(_parse_message(msg))
        return messages
    except HttpError as e:
        _handle_api_error(e)


def get_message(message_id: str, account: str = "default") -> GmailMessage:
    """Get a single message by ID with full body."""
    service = _get_gmail_service(account)
    try:
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute(num_retries=3)
        return _parse_message(msg)
    except HttpError as e:
        _handle_api_error(e)


def send_message(to: str, subject: str, body: str, account: str = "default") -> GmailMessage:
    """Compose and send a new email."""
    service = _get_gmail_service(account)
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    try:
        sent = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute(num_retries=3)
        msg = service.users().messages().get(
            userId="me", id=sent["id"], format="full"
        ).execute(num_retries=3)
        return _parse_message(msg)
    except HttpError as e:
        _handle_api_error(e)


def download_attachment(
    message_id: str, attachment_id: str, account: str = "default"
) -> tuple[bytes, str, str]:
    """Download an attachment by message ID and attachment ID.

    Returns (bytes, filename, mime_type).
    """
    service = _get_gmail_service(account)
    try:
        # Fetch message to get filename/mime_type from attachment metadata
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute(num_retries=3)
        attachments = _extract_attachments(msg["payload"])
        filename = "attachment"
        mime_type = "application/octet-stream"
        for att in attachments:
            if att.attachment_id == attachment_id:
                filename = att.filename or filename
                mime_type = att.mime_type or mime_type
                break

        # Download the attachment bytes
        att_data = service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id
        ).execute(num_retries=3)
        data = base64.urlsafe_b64decode(att_data["data"])
        return data, filename, mime_type
    except HttpError as e:
        _handle_api_error(e)


def reply_to_message(message_id: str, body: str, account: str = "default") -> GmailMessage:
    """Reply to an existing message in its thread."""
    service = _get_gmail_service(account)
    try:
        original = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute(num_retries=3)
        headers = {h["name"].lower(): h["value"] for h in original["payload"].get("headers", [])}

        mime = MIMEText(body)
        mime["to"] = headers.get("from", "")
        mime["subject"] = f"Re: {headers.get('subject', '')}"
        mime["In-Reply-To"] = headers.get("message-id", "")
        mime["References"] = headers.get("message-id", "")
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        sent = service.users().messages().send(
            userId="me", body={"raw": raw, "threadId": original["threadId"]}
        ).execute(num_retries=3)
        msg = service.users().messages().get(
            userId="me", id=sent["id"], format="full"
        ).execute(num_retries=3)
        return _parse_message(msg)
    except HttpError as e:
        _handle_api_error(e)
