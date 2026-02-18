"""Instagram service layer -- parses private API responses into Pydantic models."""

from brokenclaw.models.instagram import (
    InstagramComment,
    InstagramDirectThread,
    InstagramFollower,
    InstagramPost,
    InstagramProfile,
    InstagramReel,
    InstagramSavedPost,
    InstagramSearchResult,
    InstagramStory,
)
from brokenclaw.services.instagram_client import (
    BASE_URL,
    WEB_BASE_URL,
    instagram_get,
    instagram_get_paginated,
    instagram_post,
)


def _media_type_str(media_type: int | None) -> str | None:
    """Convert Instagram's numeric media_type to a human-readable string."""
    if media_type is None:
        return None
    return {1: "photo", 2: "video", 8: "carousel"}.get(media_type, str(media_type))


def _post_url(shortcode: str | None) -> str | None:
    if not shortcode:
        return None
    return f"https://www.instagram.com/p/{shortcode}/"


def _parse_post(item: dict) -> InstagramPost:
    """Parse an Instagram feed/user post item into a model."""
    caption_obj = item.get("caption") or {}
    caption_text = caption_obj.get("text") if isinstance(caption_obj, dict) else None
    shortcode = item.get("code")

    # Media URL: prefer image_versions2 for photos, video_versions for video
    media_url = None
    thumbnail_url = None
    image_versions = item.get("image_versions2", {})
    candidates = image_versions.get("candidates", [])
    if candidates:
        media_url = candidates[0].get("url")
        thumbnail_url = media_url

    video_versions = item.get("video_versions", [])
    if video_versions:
        media_url = video_versions[0].get("url")

    return InstagramPost(
        post_id=str(item.get("pk", "")),
        shortcode=shortcode,
        caption=caption_text,
        media_type=_media_type_str(item.get("media_type")),
        media_url=media_url,
        thumbnail_url=thumbnail_url,
        like_count=item.get("like_count"),
        comment_count=item.get("comment_count"),
        created_at=item.get("taken_at"),
        url=_post_url(shortcode),
    )


# --- Profile ---


def get_my_profile(account: str = "default") -> InstagramProfile:
    """Get the authenticated user's profile."""
    data = instagram_get("accounts/current_user/", account, params={"edit": "true"})
    user = data.get("user", {})
    return InstagramProfile(
        user_id=str(user.get("pk", "")),
        username=user.get("username"),
        full_name=user.get("full_name"),
        bio=user.get("biography"),
        profile_pic_url=user.get("profile_pic_url"),
        follower_count=user.get("follower_count"),
        following_count=user.get("following_count"),
        post_count=user.get("media_count"),
        is_private=user.get("is_private"),
        external_url=user.get("external_url"),
    )


def get_user_profile(username: str, account: str = "default") -> InstagramProfile:
    """Get any user's profile by username."""
    data = instagram_get(
        "users/web_profile_info/",
        account,
        params={"username": username},
        base_url=WEB_BASE_URL,
    )
    user = data.get("data", {}).get("user", {})
    return InstagramProfile(
        user_id=str(user.get("id", "")),
        username=user.get("username"),
        full_name=user.get("full_name"),
        bio=user.get("biography"),
        profile_pic_url=user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
        follower_count=(user.get("edge_followed_by") or {}).get("count"),
        following_count=(user.get("edge_follow") or {}).get("count"),
        post_count=(user.get("edge_owner_to_timeline_media") or {}).get("count"),
        is_private=user.get("is_private"),
        external_url=user.get("external_url"),
    )


# --- Feed ---


def get_my_feed(count: int = 20, account: str = "default") -> list[InstagramPost]:
    """Get the authenticated user's home feed."""
    data = instagram_post("feed/timeline/", account, data={"count": count})
    items = data.get("feed_items", data.get("items", []))
    posts = []
    for item in items:
        media = item.get("media_or_ad") or item
        if not media.get("pk"):
            continue
        posts.append(_parse_post(media))
    return posts


# --- User Posts ---


def get_user_posts(
    user_id: str,
    count: int = 20,
    account: str = "default",
) -> list[InstagramPost]:
    """Get a user's posts by user_id."""
    items, _ = instagram_get_paginated(
        f"feed/user/{user_id}/",
        account,
        count=count,
    )
    return [_parse_post(item) for item in items if item.get("pk")]


# --- Comments ---


def get_post_comments(
    post_id: str,
    count: int = 20,
    account: str = "default",
) -> list[InstagramComment]:
    """Get comments on a post."""
    data = instagram_get(
        f"media/{post_id}/comments/",
        account,
        params={"count": count},
    )
    comments = []
    for item in data.get("comments", []):
        user = item.get("user", {})
        comments.append(InstagramComment(
            comment_id=str(item.get("pk", "")),
            username=user.get("username"),
            text=item.get("text"),
            created_at=item.get("created_at"),
            like_count=item.get("comment_like_count"),
        ))
    return comments


# --- Stories ---


def get_my_stories(account: str = "default") -> list[InstagramStory]:
    """Get the authenticated user's story tray (stories from people they follow)."""
    data = instagram_get("feed/reels_tray/", account)
    stories = []
    for tray in data.get("tray", []):
        for item in tray.get("items", []):
            media_url = None
            video_versions = item.get("video_versions", [])
            if video_versions:
                media_url = video_versions[0].get("url")
            else:
                image_versions = item.get("image_versions2", {})
                candidates = image_versions.get("candidates", [])
                if candidates:
                    media_url = candidates[0].get("url")

            stories.append(InstagramStory(
                story_id=str(item.get("pk", "")),
                media_type=_media_type_str(item.get("media_type")),
                media_url=media_url,
                created_at=item.get("taken_at"),
                expiring_at=item.get("expiring_at"),
            ))
    return stories


def get_user_stories(
    user_id: str,
    account: str = "default",
) -> list[InstagramStory]:
    """Get a specific user's stories."""
    data = instagram_get(f"feed/user/{user_id}/story/", account)
    reel = data.get("reel") or {}
    stories = []
    for item in reel.get("items", []):
        media_url = None
        video_versions = item.get("video_versions", [])
        if video_versions:
            media_url = video_versions[0].get("url")
        else:
            image_versions = item.get("image_versions2", {})
            candidates = image_versions.get("candidates", [])
            if candidates:
                media_url = candidates[0].get("url")

        stories.append(InstagramStory(
            story_id=str(item.get("pk", "")),
            media_type=_media_type_str(item.get("media_type")),
            media_url=media_url,
            created_at=item.get("taken_at"),
            expiring_at=item.get("expiring_at"),
        ))
    return stories


# --- Reels ---


def get_user_reels(
    user_id: str,
    count: int = 20,
    account: str = "default",
) -> list[InstagramReel]:
    """Get a user's reels."""
    data = instagram_post(
        "clips/user/",
        account,
        data={"target_user_id": user_id, "page_size": count},
    )
    reels = []
    for item in data.get("items", []):
        media = item.get("media", item)
        caption_obj = media.get("caption") or {}
        caption_text = caption_obj.get("text") if isinstance(caption_obj, dict) else None
        shortcode = media.get("code")

        media_url = None
        thumbnail_url = None
        video_versions = media.get("video_versions", [])
        if video_versions:
            media_url = video_versions[0].get("url")
        image_versions = media.get("image_versions2", {})
        candidates = image_versions.get("candidates", [])
        if candidates:
            thumbnail_url = candidates[0].get("url")

        reels.append(InstagramReel(
            reel_id=str(media.get("pk", "")),
            shortcode=shortcode,
            caption=caption_text,
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            play_count=media.get("play_count"),
            like_count=media.get("like_count"),
            comment_count=media.get("comment_count"),
            created_at=media.get("taken_at"),
            url=_post_url(shortcode),
        ))
    return reels


# --- Followers / Following ---


def list_followers(
    user_id: str,
    count: int = 20,
    account: str = "default",
) -> list[InstagramFollower]:
    """List a user's followers."""
    data = instagram_get(
        f"friendships/{user_id}/followers/",
        account,
        params={"count": count},
    )
    followers = []
    for user in data.get("users", []):
        followers.append(InstagramFollower(
            user_id=str(user.get("pk", "")),
            username=user.get("username"),
            full_name=user.get("full_name"),
            profile_pic_url=user.get("profile_pic_url"),
            is_private=user.get("is_private"),
        ))
    return followers


def list_following(
    user_id: str,
    count: int = 20,
    account: str = "default",
) -> list[InstagramFollower]:
    """List users that a user is following."""
    data = instagram_get(
        f"friendships/{user_id}/following/",
        account,
        params={"count": count},
    )
    following = []
    for user in data.get("users", []):
        following.append(InstagramFollower(
            user_id=str(user.get("pk", "")),
            username=user.get("username"),
            full_name=user.get("full_name"),
            profile_pic_url=user.get("profile_pic_url"),
            is_private=user.get("is_private"),
        ))
    return following


# --- Saved Posts ---


def get_saved_posts(
    count: int = 20,
    account: str = "default",
) -> list[InstagramSavedPost]:
    """Get the authenticated user's saved posts."""
    data = instagram_get("feed/saved/posts/", account, params={"count": count})
    saved = []
    for item in data.get("items", []):
        media = item.get("media", item)
        caption_obj = media.get("caption") or {}
        caption_text = caption_obj.get("text") if isinstance(caption_obj, dict) else None
        shortcode = media.get("code")

        media_url = None
        thumbnail_url = None
        image_versions = media.get("image_versions2", {})
        candidates = image_versions.get("candidates", [])
        if candidates:
            media_url = candidates[0].get("url")
            thumbnail_url = media_url
        video_versions = media.get("video_versions", [])
        if video_versions:
            media_url = video_versions[0].get("url")

        saved.append(InstagramSavedPost(
            post_id=str(media.get("pk", "")),
            shortcode=shortcode,
            caption=caption_text,
            media_type=_media_type_str(media.get("media_type")),
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            like_count=media.get("like_count"),
            comment_count=media.get("comment_count"),
            created_at=media.get("taken_at"),
            url=_post_url(shortcode),
            saved_at=item.get("saved_at"),
        ))
    return saved


# --- Direct Messages ---


def list_direct_threads(
    count: int = 20,
    account: str = "default",
) -> list[InstagramDirectThread]:
    """List DM inbox threads."""
    data = instagram_get("direct_v2/inbox/", account, params={"limit": count})
    inbox = data.get("inbox", {})
    threads = []
    for thread in inbox.get("threads", []):
        participants = []
        for user in thread.get("users", []):
            name = user.get("full_name") or user.get("username", "")
            if name:
                participants.append(name)

        last_msg = None
        last_items = thread.get("items", [])
        if last_items:
            last_item = last_items[0]
            last_msg = last_item.get("text") or last_item.get("item_type")

        threads.append(InstagramDirectThread(
            thread_id=thread.get("thread_id"),
            thread_title=thread.get("thread_title"),
            participants=participants,
            last_message_text=last_msg,
            last_activity_at=thread.get("last_activity_at"),
            is_group=thread.get("is_group"),
        ))
    return threads


# --- Search ---


def search_users(
    query: str,
    count: int = 20,
    account: str = "default",
) -> list[InstagramSearchResult]:
    """Search for users, hashtags, and places."""
    data = instagram_get(
        "web/search/topsearch/",
        account,
        params={"query": query, "count": count},
        base_url="https://www.instagram.com",
    )
    results = []
    for item in data.get("users", []):
        user = item.get("user", {})
        username = user.get("username")
        results.append(InstagramSearchResult(
            name=user.get("full_name"),
            username=username,
            profile_pic_url=user.get("profile_pic_url"),
            follower_count=user.get("follower_count"),
            result_type="user",
            url=f"https://www.instagram.com/{username}/" if username else None,
        ))
    return results


# --- Explore ---


def get_explore(account: str = "default") -> list[InstagramPost]:
    """Get explore page posts."""
    data = instagram_get("discover/topical_explore/", account)
    posts = []
    for item in data.get("items", []):
        media = item.get("media", item)
        if not media.get("pk"):
            continue
        posts.append(_parse_post(media))
    return posts
