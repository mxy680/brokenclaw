from pydantic import BaseModel


class GmailAttachment(BaseModel):
    filename: str | None = None
    mime_type: str | None = None
    size: int | None = None
    attachment_id: str | None = None


class GmailMessage(BaseModel):
    id: str
    thread_id: str
    subject: str
    from_addr: str
    to_addr: str
    date: str
    snippet: str
    body: str | None = None
    attachments: list[GmailAttachment] = []


class SendMessageRequest(BaseModel):
    to: str
    subject: str
    body: str


class ReplyRequest(BaseModel):
    body: str


class InboxResponse(BaseModel):
    messages: list[GmailMessage]
    result_count: int
