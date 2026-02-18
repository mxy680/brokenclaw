from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_youtube_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.youtube import (
    ChannelInfo,
    PlaylistInfo,
    PlaylistItem,
    VideoDetail,
    VideoResult,
)


def _get_youtube_service(account: str = "default"):
    try:
        creds = get_youtube_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain YouTube credentials: {e}. Visit /auth/youtube/setup?account={account}."
        ) from e
    return build("youtube", "v3", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("YouTube API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "YouTube credentials expired or revoked. Visit /auth/youtube/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"YouTube API error: {e}") from e


def _video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _channel_url(channel_id: str) -> str:
    return f"https://www.youtube.com/channel/{channel_id}"


def _playlist_url(playlist_id: str) -> str:
    return f"https://www.youtube.com/playlist?list={playlist_id}"


def _best_thumbnail(thumbnails: dict) -> str | None:
    for key in ("high", "medium", "default"):
        if key in thumbnails:
            return thumbnails[key].get("url")
    return None


def search_videos(query: str, max_results: int = 10, account: str = "default") -> list[VideoResult]:
    """Search YouTube for videos."""
    service = _get_youtube_service(account)
    try:
        result = service.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=min(max_results, 50),
        ).execute(num_retries=3)
        videos = []
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            videos.append(VideoResult(
                id=video_id,
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                channel_title=snippet.get("channelTitle", ""),
                published_at=snippet.get("publishedAt", ""),
                thumbnail_url=_best_thumbnail(snippet.get("thumbnails", {})),
                url=_video_url(video_id),
            ))
        return videos
    except HttpError as e:
        _handle_api_error(e)


def get_video(video_id: str, account: str = "default") -> VideoDetail:
    """Get detailed information about a video."""
    service = _get_youtube_service(account)
    try:
        result = service.videos().list(
            id=video_id,
            part="snippet,contentDetails,statistics",
        ).execute(num_retries=3)
        items = result.get("items", [])
        if not items:
            raise IntegrationError(f"Video not found: {video_id}")
        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        return VideoDetail(
            id=item["id"],
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            channel_title=snippet.get("channelTitle", ""),
            channel_id=snippet.get("channelId", ""),
            published_at=snippet.get("publishedAt", ""),
            tags=snippet.get("tags", []),
            duration=content.get("duration"),
            view_count=int(stats["viewCount"]) if "viewCount" in stats else None,
            like_count=int(stats["likeCount"]) if "likeCount" in stats else None,
            comment_count=int(stats["commentCount"]) if "commentCount" in stats else None,
            thumbnail_url=_best_thumbnail(snippet.get("thumbnails", {})),
            url=_video_url(item["id"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def get_channel(channel_id: str, account: str = "default") -> ChannelInfo:
    """Get channel information."""
    service = _get_youtube_service(account)
    try:
        result = service.channels().list(
            id=channel_id,
            part="snippet,statistics",
        ).execute(num_retries=3)
        items = result.get("items", [])
        if not items:
            raise IntegrationError(f"Channel not found: {channel_id}")
        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        return ChannelInfo(
            id=item["id"],
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            subscriber_count=int(stats["subscriberCount"]) if "subscriberCount" in stats else None,
            video_count=int(stats["videoCount"]) if "videoCount" in stats else None,
            view_count=int(stats["viewCount"]) if "viewCount" in stats else None,
            thumbnail_url=_best_thumbnail(snippet.get("thumbnails", {})),
            url=_channel_url(item["id"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def list_playlists(channel_id: str | None = None, max_results: int = 25, account: str = "default") -> list[PlaylistInfo]:
    """List playlists. If channel_id is None, lists the authenticated user's playlists."""
    service = _get_youtube_service(account)
    try:
        params = {
            "part": "snippet,contentDetails",
            "maxResults": min(max_results, 50),
        }
        if channel_id:
            params["channelId"] = channel_id
        else:
            params["mine"] = True
        result = service.playlists().list(**params).execute(num_retries=3)
        playlists = []
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            playlists.append(PlaylistInfo(
                id=item["id"],
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                item_count=content.get("itemCount"),
                thumbnail_url=_best_thumbnail(snippet.get("thumbnails", {})),
                url=_playlist_url(item["id"]),
            ))
        return playlists
    except HttpError as e:
        _handle_api_error(e)


def list_playlist_items(playlist_id: str, max_results: int = 50, account: str = "default") -> list[PlaylistItem]:
    """List videos in a playlist."""
    service = _get_youtube_service(account)
    try:
        result = service.playlistItems().list(
            playlistId=playlist_id,
            part="snippet",
            maxResults=min(max_results, 50),
        ).execute(num_retries=3)
        items = []
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId", "")
            items.append(PlaylistItem(
                video_id=video_id,
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                position=snippet.get("position", 0),
                thumbnail_url=_best_thumbnail(snippet.get("thumbnails", {})),
                url=_video_url(video_id),
            ))
        return items
    except HttpError as e:
        _handle_api_error(e)
