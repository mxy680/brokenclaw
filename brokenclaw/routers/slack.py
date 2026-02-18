from fastapi import APIRouter

from brokenclaw.models.slack import (
    SlackChannel,
    SlackMessage,
    SlackPostResult,
    SlackSearchResult,
    SlackUser,
)
from brokenclaw.services import slack as slack_service

router = APIRouter(prefix="/api/slack", tags=["slack"])


@router.get("/channels")
def list_channels(exclude_archived: bool = True, max_results: int = 100) -> list[SlackChannel]:
    return slack_service.list_channels(exclude_archived, max_results)


@router.get("/channels/{channel_id}/history")
def get_channel_history(
    channel_id: str,
    max_results: int = 20,
    oldest: str | None = None,
    latest: str | None = None,
) -> list[SlackMessage]:
    return slack_service.get_channel_history(channel_id, max_results, oldest, latest)


@router.get("/channels/{channel_id}/threads/{thread_ts}")
def get_thread_replies(channel_id: str, thread_ts: str, max_results: int = 50) -> list[SlackMessage]:
    return slack_service.get_thread_replies(channel_id, thread_ts, max_results)


@router.post("/channels/{channel_id}/messages")
def send_message(channel_id: str, text: str, thread_ts: str | None = None) -> SlackPostResult:
    return slack_service.send_message(channel_id, text, thread_ts)


@router.get("/search")
def search_messages(query: str, max_results: int = 20) -> SlackSearchResult:
    return slack_service.search_messages(query, max_results)


@router.get("/users")
def list_users(max_results: int = 100) -> list[SlackUser]:
    return slack_service.list_users(max_results)


@router.post("/channels/{channel_id}/messages/{timestamp}/reactions")
def add_reaction(channel_id: str, timestamp: str, emoji: str):
    return slack_service.add_reaction(channel_id, timestamp, emoji)
