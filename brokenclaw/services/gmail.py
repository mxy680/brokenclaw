import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from brokenclaw.auth import get_gmail_credentials
from brokenclaw.models.gmail import GmailMessage


def _get_gmail_service():
    creds = get_gmail_credentials()
    return build("gmail", "v1", credentials=creds)


def _parse_message(msg: dict) -> GmailMessage:
    """Extract a GmailMessage from the Gmail API message resource."""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    # Extract body text
    body = _extract_body(msg["payload"])
    return GmailMessage(
        id=msg["id"],
        thread_id=msg["threadId"],
        subject=headers.get("subject", ""),
        from_addr=headers.get("from", ""),
        to_addr=headers.get("to", ""),
        date=headers.get("date", ""),
        snippet=msg.get("snippet", ""),
        body=body,
    )


def _extract_body(payload: dict) -> str | None:
    """Recursively extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text
    return None


def get_inbox(max_results: int = 20) -> list[GmailMessage]:
    """Get recent inbox messages."""
    service = _get_gmail_service()
    results = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max_results
    ).execute()
    messages = []
    for msg_ref in results.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()
        messages.append(_parse_message(msg))
    return messages


def search_messages(query: str, max_results: int = 20) -> list[GmailMessage]:
    """Search messages using Gmail query syntax."""
    service = _get_gmail_service()
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = []
    for msg_ref in results.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()
        messages.append(_parse_message(msg))
    return messages


def get_message(message_id: str) -> GmailMessage:
    """Get a single message by ID with full body."""
    service = _get_gmail_service()
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    return _parse_message(msg)


def send_message(to: str, subject: str, body: str) -> GmailMessage:
    """Compose and send a new email."""
    service = _get_gmail_service()
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    # Fetch the full sent message to return structured data
    msg = service.users().messages().get(
        userId="me", id=sent["id"], format="full"
    ).execute()
    return _parse_message(msg)


def reply_to_message(message_id: str, body: str) -> GmailMessage:
    """Reply to an existing message in its thread."""
    service = _get_gmail_service()
    original = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    headers = {h["name"].lower(): h["value"] for h in original["payload"].get("headers", [])}

    mime = MIMEText(body)
    mime["to"] = headers.get("from", "")
    mime["subject"] = f"Re: {headers.get('subject', '')}"
    mime["In-Reply-To"] = headers.get("message-id", "")
    mime["References"] = headers.get("message-id", "")
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

    sent = service.users().messages().send(
        userId="me", body={"raw": raw, "threadId": original["threadId"]}
    ).execute()
    msg = service.users().messages().get(
        userId="me", id=sent["id"], format="full"
    ).execute()
    return _parse_message(msg)
