from pydantic import BaseModel


class VideoResult(BaseModel):
    id: str
    title: str
    description: str
    channel_title: str
    published_at: str
    thumbnail_url: str | None = None
    url: str


class VideoDetail(BaseModel):
    id: str
    title: str
    description: str
    channel_title: str
    channel_id: str
    published_at: str
    tags: list[str] = []
    duration: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    thumbnail_url: str | None = None
    url: str


class ChannelInfo(BaseModel):
    id: str
    title: str
    description: str
    subscriber_count: int | None = None
    video_count: int | None = None
    view_count: int | None = None
    thumbnail_url: str | None = None
    url: str


class PlaylistInfo(BaseModel):
    id: str
    title: str
    description: str
    item_count: int | None = None
    thumbnail_url: str | None = None
    url: str


class PlaylistItem(BaseModel):
    video_id: str
    title: str
    description: str
    position: int
    thumbnail_url: str | None = None
    url: str
