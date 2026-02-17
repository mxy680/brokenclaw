from fastapi import APIRouter

from brokenclaw.models.youtube import (
    ChannelInfo,
    PlaylistInfo,
    PlaylistItem,
    VideoDetail,
    VideoResult,
)
from brokenclaw.services import youtube as youtube_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.get("/search")
def search_videos(query: str, max_results: int = 10, account: str = "default") -> list[VideoResult]:
    return youtube_service.search_videos(query, max_results, account=account)


@router.get("/videos/{video_id}")
def get_video(video_id: str, account: str = "default") -> VideoDetail:
    return youtube_service.get_video(video_id, account=account)


@router.get("/channels/{channel_id}")
def get_channel(channel_id: str, account: str = "default") -> ChannelInfo:
    return youtube_service.get_channel(channel_id, account=account)


@router.get("/playlists")
def list_playlists(channel_id: str | None = None, max_results: int = 25, account: str = "default") -> list[PlaylistInfo]:
    return youtube_service.list_playlists(channel_id, max_results, account=account)


@router.get("/playlists/{playlist_id}/items")
def list_playlist_items(playlist_id: str, max_results: int = 50, account: str = "default") -> list[PlaylistItem]:
    return youtube_service.list_playlist_items(playlist_id, max_results, account=account)
