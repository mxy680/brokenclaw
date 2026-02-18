import io

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from brokenclaw.models.slack import (
    SlackConversation,
    SlackMessage,
    SlackProfile,
    SlackSearchResult,
)
from brokenclaw.services import slack as slack_service

router = APIRouter(prefix="/api/slack", tags=["slack"])


@router.get("/files/{file_id}")
def download_file(file_id: str, account: str = "default"):
    data, filename, mime_type = slack_service.download_file(file_id, account)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/profile")
def profile(account: str = "default") -> SlackProfile:
    return slack_service.get_my_profile(account)


@router.get("/profile/{user_id}")
def user_profile(user_id: str, account: str = "default") -> SlackProfile:
    return slack_service.get_user_profile(user_id, account)


@router.get("/conversations")
def conversations(
    types: str = "public_channel,private_channel,mpim,im",
    count: int = 100,
    account: str = "default",
) -> list[SlackConversation]:
    return slack_service.list_conversations(types, count, account)


@router.get("/conversations/{channel_id}")
def conversation_info(channel_id: str, account: str = "default") -> SlackConversation:
    return slack_service.get_conversation_info(channel_id, account)


@router.get("/messages/{channel_id}")
def messages(channel_id: str, count: int = 15, account: str = "default") -> list[SlackMessage]:
    return slack_service.get_messages(channel_id, count, account)


@router.get("/threads/{channel_id}/{thread_ts}")
def thread_replies(channel_id: str, thread_ts: str, count: int = 50, account: str = "default") -> list[SlackMessage]:
    return slack_service.get_thread_replies(channel_id, thread_ts, count, account)


@router.get("/search")
def search(query: str, count: int = 20, account: str = "default") -> list[SlackSearchResult]:
    return slack_service.search_messages(query, count, account)


@router.get("/users")
def users(count: int = 100, account: str = "default") -> list[SlackProfile]:
    return slack_service.list_users(count, account)
