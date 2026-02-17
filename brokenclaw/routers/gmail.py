from fastapi import APIRouter

from brokenclaw.models.gmail import (
    GmailMessage,
    InboxResponse,
    ReplyRequest,
    SendMessageRequest,
)
from brokenclaw.services import gmail as gmail_service

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/inbox")
def inbox(max_results: int = 20) -> InboxResponse:
    messages = gmail_service.get_inbox(max_results)
    return InboxResponse(messages=messages, result_count=len(messages))


@router.get("/search")
def search(query: str, max_results: int = 20) -> InboxResponse:
    messages = gmail_service.search_messages(query, max_results)
    return InboxResponse(messages=messages, result_count=len(messages))


@router.get("/messages/{message_id}")
def get_message(message_id: str) -> GmailMessage:
    return gmail_service.get_message(message_id)


@router.post("/send")
def send(request: SendMessageRequest) -> GmailMessage:
    return gmail_service.send_message(request.to, request.subject, request.body)


@router.post("/messages/{message_id}/reply")
def reply(message_id: str, request: ReplyRequest) -> GmailMessage:
    return gmail_service.reply_to_message(message_id, request.body)
