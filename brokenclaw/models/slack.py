from pydantic import BaseModel


class SlackChannel(BaseModel):
    id: str
    name: str
    is_private: bool = False
    is_im: bool = False
    topic: str | None = None
    purpose: str | None = None
    num_members: int | None = None


class SlackUser(BaseModel):
    id: str
    name: str
    real_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    is_bot: bool = False
    timezone: str | None = None


class SlackMessage(BaseModel):
    ts: str
    user: str | None = None
    user_name: str | None = None
    text: str
    channel: str | None = None
    thread_ts: str | None = None
    reply_count: int | None = None
    reactions: list[str] = []
    permalink: str | None = None


class SlackSearchResult(BaseModel):
    query: str
    total: int
    messages: list[SlackMessage]


class SlackPostResult(BaseModel):
    ok: bool
    channel: str
    ts: str
    message_text: str
