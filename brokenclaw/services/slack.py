"""Slack service layer -- parses web API responses into Pydantic models."""

from brokenclaw.models.slack import (
    SlackConversation,
    SlackFile,
    SlackMessage,
    SlackProfile,
    SlackSearchResult,
)
from brokenclaw.services.slack_client import slack_api, slack_api_paginated


def _parse_profile(user: dict) -> SlackProfile:
    """Parse a Slack user object into a SlackProfile."""
    profile = user.get("profile", {})
    return SlackProfile(
        user_id=user.get("id"),
        username=user.get("name"),
        real_name=user.get("real_name") or profile.get("real_name"),
        display_name=profile.get("display_name"),
        email=profile.get("email"),
        profile_pic_url=profile.get("image_192") or profile.get("image_72"),
        title=profile.get("title"),
        status_text=profile.get("status_text"),
        is_bot=user.get("is_bot"),
    )


def _parse_message(msg: dict) -> SlackMessage:
    """Parse a Slack message object into a SlackMessage."""
    reactions = msg.get("reactions", [])
    reactions_summary = None
    if reactions:
        parts = [f":{r.get('name', '?')}: ({r.get('count', 0)})" for r in reactions[:5]]
        reactions_summary = ", ".join(parts)

    files = [
        SlackFile(
            file_id=f.get("id"),
            name=f.get("name"),
            title=f.get("title"),
            mime_type=f.get("mimetype"),
            size=f.get("size"),
            url=f.get("url_private"),
        )
        for f in msg.get("files", [])
    ]

    return SlackMessage(
        ts=msg.get("ts"),
        user_id=msg.get("user"),
        username=msg.get("username"),
        text=msg.get("text"),
        thread_ts=msg.get("thread_ts"),
        reply_count=msg.get("reply_count"),
        reactions_summary=reactions_summary,
        files=files,
    )


# --- Profile ---


def get_my_profile(account: str = "default") -> SlackProfile:
    """Get the authenticated user's profile."""
    auth_data = slack_api("auth.test", account)
    user_id = auth_data.get("user_id")
    return get_user_profile(user_id, account)


def get_user_profile(user_id: str, account: str = "default") -> SlackProfile:
    """Get a user's profile by user_id."""
    data = slack_api("users.info", account, {"user": user_id})
    user = data.get("user", {})
    return _parse_profile(user)


# --- Conversations ---


def list_conversations(
    types: str = "public_channel,private_channel,mpim,im",
    count: int = 100,
    account: str = "default",
) -> list[SlackConversation]:
    """List conversations (channels, DMs, group DMs).

    types: comma-separated list of conversation types to include.
    """
    channels = slack_api_paginated(
        "conversations.list",
        account,
        params={"types": types, "exclude_archived": "true"},
        result_key="channels",
        count=count,
    )
    conversations = []
    for ch in channels:
        conversations.append(SlackConversation(
            channel_id=ch.get("id"),
            name=ch.get("name") or ch.get("name_normalized"),
            topic=(ch.get("topic") or {}).get("value"),
            purpose=(ch.get("purpose") or {}).get("value"),
            is_channel=ch.get("is_channel"),
            is_dm=ch.get("is_im"),
            is_group=ch.get("is_mpim"),
            is_private=ch.get("is_private"),
            member_count=ch.get("num_members"),
            created=ch.get("created"),
        ))
    return conversations


def get_conversation_info(
    channel_id: str,
    account: str = "default",
) -> SlackConversation:
    """Get info about a specific conversation."""
    data = slack_api("conversations.info", account, {"channel": channel_id})
    ch = data.get("channel", {})
    return SlackConversation(
        channel_id=ch.get("id"),
        name=ch.get("name") or ch.get("name_normalized"),
        topic=(ch.get("topic") or {}).get("value"),
        purpose=(ch.get("purpose") or {}).get("value"),
        is_channel=ch.get("is_channel"),
        is_dm=ch.get("is_im"),
        is_group=ch.get("is_mpim"),
        is_private=ch.get("is_private"),
        member_count=ch.get("num_members"),
        created=ch.get("created"),
    )


# --- Messages ---


def get_messages(
    channel_id: str,
    count: int = 15,
    account: str = "default",
) -> list[SlackMessage]:
    """Get message history for a conversation."""
    data = slack_api("conversations.history", account, {
        "channel": channel_id,
        "limit": count,
    })
    messages = []
    for msg in data.get("messages", []):
        parsed = _parse_message(msg)
        parsed.channel_id = channel_id
        messages.append(parsed)
    return messages


def get_thread_replies(
    channel_id: str,
    thread_ts: str,
    count: int = 50,
    account: str = "default",
) -> list[SlackMessage]:
    """Get replies in a thread."""
    data = slack_api("conversations.replies", account, {
        "channel": channel_id,
        "ts": thread_ts,
        "limit": count,
    })
    messages = []
    for msg in data.get("messages", []):
        parsed = _parse_message(msg)
        parsed.channel_id = channel_id
        messages.append(parsed)
    return messages


# --- Search ---


def search_messages(
    query: str,
    count: int = 20,
    account: str = "default",
) -> list[SlackSearchResult]:
    """Search messages across the workspace."""
    data = slack_api("search.messages", account, {
        "query": query,
        "count": count,
    })
    matches = (data.get("messages") or {}).get("matches", [])
    results = []
    for match in matches:
        results.append(SlackSearchResult(
            text=match.get("text"),
            username=match.get("username"),
            channel_name=(match.get("channel") or {}).get("name"),
            ts=match.get("ts"),
            permalink=match.get("permalink"),
        ))
    return results


# --- Users ---


def list_users(
    count: int = 100,
    account: str = "default",
) -> list[SlackProfile]:
    """List workspace users."""
    members = slack_api_paginated(
        "users.list",
        account,
        result_key="members",
        count=count,
    )
    users = []
    for user in members:
        if user.get("deleted"):
            continue
        users.append(_parse_profile(user))
    return users
