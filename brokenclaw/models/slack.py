from pydantic import BaseModel


class SlackProfile(BaseModel):
    user_id: str | None = None
    username: str | None = None
    real_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    profile_pic_url: str | None = None
    title: str | None = None
    status_text: str | None = None
    is_bot: bool | None = None


class SlackConversation(BaseModel):
    channel_id: str | None = None
    name: str | None = None
    topic: str | None = None
    purpose: str | None = None
    is_channel: bool | None = None
    is_dm: bool | None = None
    is_group: bool | None = None
    is_private: bool | None = None
    member_count: int | None = None
    created: int | None = None


class SlackFile(BaseModel):
    file_id: str | None = None
    name: str | None = None
    title: str | None = None
    mime_type: str | None = None
    size: int | None = None
    url: str | None = None


class SlackMessage(BaseModel):
    ts: str | None = None
    user_id: str | None = None
    username: str | None = None
    text: str | None = None
    channel_id: str | None = None
    thread_ts: str | None = None
    reply_count: int | None = None
    reactions_summary: str | None = None
    files: list[SlackFile] = []


class SlackSearchResult(BaseModel):
    text: str | None = None
    username: str | None = None
    channel_name: str | None = None
    ts: str | None = None
    permalink: str | None = None
