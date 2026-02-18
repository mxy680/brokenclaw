from pydantic import BaseModel


class InstagramProfile(BaseModel):
    user_id: str | None = None
    username: str | None = None
    full_name: str | None = None
    bio: str | None = None
    profile_pic_url: str | None = None
    follower_count: int | None = None
    following_count: int | None = None
    post_count: int | None = None
    is_private: bool | None = None
    external_url: str | None = None


class InstagramMediaItem(BaseModel):
    media_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None


class InstagramPost(BaseModel):
    post_id: str | None = None
    shortcode: str | None = None
    caption: str | None = None
    media_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    like_count: int | None = None
    comment_count: int | None = None
    created_at: int | None = None
    url: str | None = None
    carousel_items: list[InstagramMediaItem] = []


class InstagramComment(BaseModel):
    comment_id: str | None = None
    username: str | None = None
    text: str | None = None
    created_at: int | None = None
    like_count: int | None = None


class InstagramStory(BaseModel):
    story_id: str | None = None
    media_type: str | None = None
    media_url: str | None = None
    created_at: int | None = None
    expiring_at: int | None = None


class InstagramReel(BaseModel):
    reel_id: str | None = None
    shortcode: str | None = None
    caption: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    play_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    created_at: int | None = None
    url: str | None = None


class InstagramFollower(BaseModel):
    user_id: str | None = None
    username: str | None = None
    full_name: str | None = None
    profile_pic_url: str | None = None
    is_private: bool | None = None


class InstagramDirectThread(BaseModel):
    thread_id: str | None = None
    thread_title: str | None = None
    participants: list[str] = []
    last_message_text: str | None = None
    last_message_media_type: str | None = None
    last_message_media_url: str | None = None
    last_activity_at: int | None = None
    is_group: bool | None = None


class InstagramSearchResult(BaseModel):
    name: str | None = None
    username: str | None = None
    profile_pic_url: str | None = None
    follower_count: int | None = None
    result_type: str | None = None
    url: str | None = None


class InstagramSavedPost(BaseModel):
    post_id: str | None = None
    shortcode: str | None = None
    caption: str | None = None
    media_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    like_count: int | None = None
    comment_count: int | None = None
    created_at: int | None = None
    url: str | None = None
    saved_at: int | None = None
