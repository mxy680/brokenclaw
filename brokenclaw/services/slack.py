import requests

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.slack import (
    SlackChannel,
    SlackMessage,
    SlackPostResult,
    SlackSearchResult,
    SlackUser,
)
from brokenclaw.slack_auth import get_slack_token

SLACK_API = "https://slack.com/api"


def _headers() -> dict:
    return {"Authorization": f"Bearer {get_slack_token()}"}


def _handle_response(resp: requests.Response) -> dict:
    if resp.status_code == 429:
        raise RateLimitError("Slack API rate limit exceeded. Try again shortly.")
    if resp.status_code in (401, 403):
        raise AuthenticationError("Slack token invalid or revoked. Visit /auth/slack/setup.")
    data = resp.json()
    if not data.get("ok"):
        error = data.get("error", "unknown_error")
        if error in ("token_revoked", "invalid_auth", "not_authed"):
            raise AuthenticationError(f"Slack auth error: {error}. Visit /auth/slack/setup.")
        if error == "ratelimited":
            raise RateLimitError("Slack API rate limit exceeded.")
        raise IntegrationError(f"Slack API error: {error}")
    return data


def list_channels(exclude_archived: bool = True, max_results: int = 100) -> list[SlackChannel]:
    """List channels the user is a member of."""
    resp = requests.get(
        f"{SLACK_API}/conversations.list",
        headers=_headers(),
        params={
            "types": "public_channel,private_channel",
            "exclude_archived": str(exclude_archived).lower(),
            "limit": min(max_results, 1000),
        },
    )
    data = _handle_response(resp)
    channels = []
    for ch in data.get("channels", []):
        channels.append(SlackChannel(
            id=ch["id"],
            name=ch.get("name", ""),
            is_private=ch.get("is_private", False),
            topic=ch.get("topic", {}).get("value") or None,
            purpose=ch.get("purpose", {}).get("value") or None,
            num_members=ch.get("num_members"),
        ))
    return channels


def get_channel_history(
    channel_id: str,
    max_results: int = 20,
    oldest: str | None = None,
    latest: str | None = None,
) -> list[SlackMessage]:
    """Get recent messages from a channel."""
    params = {
        "channel": channel_id,
        "limit": min(max_results, 100),
    }
    if oldest:
        params["oldest"] = oldest
    if latest:
        params["latest"] = latest
    resp = requests.get(
        f"{SLACK_API}/conversations.history",
        headers=_headers(),
        params=params,
    )
    data = _handle_response(resp)
    messages = []
    for msg in data.get("messages", []):
        reactions = [r.get("name", "") for r in msg.get("reactions", [])]
        messages.append(SlackMessage(
            ts=msg["ts"],
            user=msg.get("user"),
            text=msg.get("text", ""),
            channel=channel_id,
            thread_ts=msg.get("thread_ts"),
            reply_count=msg.get("reply_count"),
            reactions=reactions,
        ))
    return messages


def get_thread_replies(channel_id: str, thread_ts: str, max_results: int = 50) -> list[SlackMessage]:
    """Get replies in a thread."""
    resp = requests.get(
        f"{SLACK_API}/conversations.replies",
        headers=_headers(),
        params={
            "channel": channel_id,
            "ts": thread_ts,
            "limit": min(max_results, 100),
        },
    )
    data = _handle_response(resp)
    messages = []
    for msg in data.get("messages", []):
        reactions = [r.get("name", "") for r in msg.get("reactions", [])]
        messages.append(SlackMessage(
            ts=msg["ts"],
            user=msg.get("user"),
            text=msg.get("text", ""),
            channel=channel_id,
            thread_ts=msg.get("thread_ts"),
            reply_count=msg.get("reply_count"),
            reactions=reactions,
        ))
    return messages


def send_message(channel_id: str, text: str, thread_ts: str | None = None) -> SlackPostResult:
    """Send a message to a channel (or reply to a thread)."""
    payload = {
        "channel": channel_id,
        "text": text,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
    resp = requests.post(
        f"{SLACK_API}/chat.postMessage",
        headers=_headers(),
        json=payload,
    )
    data = _handle_response(resp)
    return SlackPostResult(
        ok=True,
        channel=data.get("channel", channel_id),
        ts=data.get("ts", ""),
        message_text=text,
    )


def search_messages(query: str, max_results: int = 20) -> SlackSearchResult:
    """Search messages across the workspace."""
    resp = requests.get(
        f"{SLACK_API}/search.messages",
        headers=_headers(),
        params={
            "query": query,
            "count": min(max_results, 100),
            "sort": "timestamp",
            "sort_dir": "desc",
        },
    )
    data = _handle_response(resp)
    matches_data = data.get("messages", {})
    total = matches_data.get("total", 0)
    messages = []
    for match in matches_data.get("matches", []):
        messages.append(SlackMessage(
            ts=match.get("ts", ""),
            user=match.get("user"),
            user_name=match.get("username"),
            text=match.get("text", ""),
            channel=match.get("channel", {}).get("id") if isinstance(match.get("channel"), dict) else match.get("channel"),
            thread_ts=match.get("thread_ts"),
            permalink=match.get("permalink"),
        ))
    return SlackSearchResult(query=query, total=total, messages=messages)


def list_users(max_results: int = 100) -> list[SlackUser]:
    """List users in the workspace."""
    resp = requests.get(
        f"{SLACK_API}/users.list",
        headers=_headers(),
        params={"limit": min(max_results, 200)},
    )
    data = _handle_response(resp)
    users = []
    for member in data.get("members", []):
        if member.get("deleted"):
            continue
        profile = member.get("profile", {})
        users.append(SlackUser(
            id=member["id"],
            name=member.get("name", ""),
            real_name=member.get("real_name") or profile.get("real_name"),
            display_name=profile.get("display_name") or None,
            email=profile.get("email"),
            is_bot=member.get("is_bot", False),
            timezone=member.get("tz"),
        ))
    return users


def add_reaction(channel_id: str, timestamp: str, emoji: str) -> dict:
    """Add a reaction emoji to a message."""
    resp = requests.post(
        f"{SLACK_API}/reactions.add",
        headers=_headers(),
        json={
            "channel": channel_id,
            "timestamp": timestamp,
            "name": emoji,
        },
    )
    _handle_response(resp)
    return {"ok": True, "emoji": emoji}
