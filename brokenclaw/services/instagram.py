"""Instagram service layer -- parses web API responses into Pydantic models."""

from brokenclaw.exceptions import IntegrationError
from brokenclaw.models.instagram import (
    InstagramComment,
    InstagramDirectThread,
    InstagramFollower,
    InstagramMediaItem,
    InstagramPost,
    InstagramProfile,
    InstagramReel,
    InstagramSavedPost,
    InstagramSearchResult,
    InstagramStory,
)
from brokenclaw.services.instagram_client import (
    instagram_get,
    instagram_get_paginated,
    instagram_post,
)


def download_media(url: str) -> tuple[bytes, str, str]:
    """Download Instagram media from a CDN URL.

    CDN URLs (fbcdn.net/cdninstagram.com) are signed and publicly accessible
    — no auth headers needed. Returns (bytes, filename, mime_type).
    """
    from posixpath import basename
    from urllib.parse import urlparse

    from curl_cffi import requests as curl_requests

    from brokenclaw.exceptions import IntegrationError

    resp = curl_requests.get(url, impersonate="chrome", allow_redirects=True)
    if resp.status_code >= 400:
        raise IntegrationError(
            f"Instagram media download error (HTTP {resp.status_code})"
        )

    mime_type = resp.headers.get("content-type", "application/octet-stream")
    # Infer filename from URL path (strip query params)
    path = urlparse(url).path
    filename = basename(path) or "media"

    return resp.content, filename, mime_type


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

    # Carousel children (media_type == 8)
    carousel_items = []
    if item.get("media_type") == 8:
        for child in item.get("carousel_media", []):
            child_media_url = None
            child_thumbnail_url = None
            child_images = child.get("image_versions2", {})
            child_candidates = child_images.get("candidates", [])
            if child_candidates:
                child_media_url = child_candidates[0].get("url")
                child_thumbnail_url = child_media_url
            child_videos = child.get("video_versions", [])
            if child_videos:
                child_media_url = child_videos[0].get("url")
            carousel_items.append(InstagramMediaItem(
                media_type=_media_type_str(child.get("media_type")),
                media_url=child_media_url,
                thumbnail_url=child_thumbnail_url,
            ))

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
        carousel_items=carousel_items,
    )


# --- Profile ---


def get_my_profile(account: str = "default") -> InstagramProfile:
    """Get the authenticated user's profile.

    Uses web_profile_info with the username from config, since
    accounts/current_user is a mobile-only endpoint.
    """
    from brokenclaw.config import get_settings
    from brokenclaw.services.instagram_auth import get_instagram_session

    # Try username from session's all_cookies (ds_user_id) -> need username though
    # Fall back to config
    session = get_instagram_session(account)
    username = get_settings().instagram_username
    if not username:
        raise IntegrationError("INSTAGRAM_USERNAME not set in .env — needed for profile lookup")
    return get_user_profile(username, account)


def get_user_profile(username: str, account: str = "default") -> InstagramProfile:
    """Get any user's profile by username."""
    data = instagram_get(
        "users/web_profile_info/",
        account,
        params={"username": username},
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
        last_media_type = None
        last_media_url = None
        last_items = thread.get("items", [])
        if last_items:
            last_item = last_items[0]
            last_msg = last_item.get("text") or last_item.get("item_type")

            # Extract media info from DM item
            item_type = last_item.get("item_type")
            media_obj = None
            if item_type == "media":
                media_obj = last_item.get("media")
            elif item_type == "reel_share":
                media_obj = (last_item.get("reel_share") or {}).get("media")
            elif item_type == "media_share":
                media_obj = (last_item.get("media_share") or last_item.get("media"))
            elif item_type == "clip":
                media_obj = (last_item.get("clip") or {}).get("clip")
            elif item_type == "voice_media":
                voice = last_item.get("voice_media") or {}
                media_obj = voice.get("media")

            if isinstance(media_obj, dict):
                last_media_type = _media_type_str(media_obj.get("media_type"))
                # Try video first, then image
                vv = media_obj.get("video_versions", [])
                if vv:
                    last_media_url = vv[0].get("url")
                else:
                    iv = media_obj.get("image_versions2", {}).get("candidates", [])
                    if iv:
                        last_media_url = iv[0].get("url")

        threads.append(InstagramDirectThread(
            thread_id=thread.get("thread_id"),
            thread_title=thread.get("thread_title"),
            participants=participants,
            last_message_text=last_msg,
            last_message_media_type=last_media_type,
            last_message_media_url=last_media_url,
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
    # Note: search uses the www root, not /api/v1/
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
    """Get explore page posts.

    Uses the explore grid endpoint (web API compatible).
    """
    try:
        data = instagram_get("discover/web/explore_grid/", account)
    except IntegrationError:
        # Fallback: explore endpoints may not work on all sessions
        return []
    posts = []
    for section in data.get("sectional_items", data.get("items", [])):
        layout_content = section.get("layout_content", {})
        medias = layout_content.get("medias", [])
        for m in medias:
            media = m.get("media", {})
            if media.get("pk"):
                posts.append(_parse_post(media))
    return posts
