from brokenclaw.models.youtube import (
    ChannelInfo,
    PlaylistInfo,
    PlaylistItem,
    VideoDetail,
    VideoResult,
)
from brokenclaw.services import youtube as youtube_service
from tests.conftest import requires_youtube


@requires_youtube
class TestSearchVideos:
    def test_search(self):
        results = youtube_service.search_videos("Python tutorial", max_results=3)
        assert isinstance(results, list)
        assert len(results) > 0
        video = results[0]
        assert isinstance(video, VideoResult)
        assert video.id
        assert video.title
        assert "youtube.com/watch" in video.url


@requires_youtube
class TestGetVideo:
    def test_get_video(self):
        # Use "Never Gonna Give You Up" — a stable, well-known video
        detail = youtube_service.get_video("dQw4w9WgXcQ")
        assert isinstance(detail, VideoDetail)
        assert detail.id == "dQw4w9WgXcQ"
        assert detail.title
        assert detail.channel_title
        assert detail.view_count is not None
        assert detail.view_count > 0
        assert "youtube.com/watch" in detail.url


@requires_youtube
class TestGetChannel:
    def test_get_channel(self):
        # Google's official YouTube channel
        channel = youtube_service.get_channel("UCVHFbqXqoYvEWM1Ddxl0QDg")
        assert isinstance(channel, ChannelInfo)
        assert channel.id == "UCVHFbqXqoYvEWM1Ddxl0QDg"
        assert channel.title
        assert "youtube.com/channel" in channel.url


@requires_youtube
class TestListPlaylists:
    def test_list_own_playlists(self):
        playlists = youtube_service.list_playlists(max_results=5)
        assert isinstance(playlists, list)
        # User may or may not have playlists, just verify structure
        for p in playlists:
            assert isinstance(p, PlaylistInfo)
            assert p.id
            assert "youtube.com/playlist" in p.url


@requires_youtube
class TestListPlaylistItems:
    def test_list_items(self):
        # YouTube's "Popular Right Now" playlist (global)
        # Use "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf" — YouTube's Music playlist
        # Instead, search for a known stable playlist. Use "PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI" — TED-Ed's most popular
        results = youtube_service.search_videos("TED-Ed", max_results=1)
        if results:
            # Just verify the function runs without error for any playlist
            pass
        # Test with a known playlist if available - list user's own playlists first
        playlists = youtube_service.list_playlists(max_results=1)
        if playlists:
            items = youtube_service.list_playlist_items(playlists[0].id, max_results=5)
            assert isinstance(items, list)
            for item in items:
                assert isinstance(item, PlaylistItem)
                assert item.video_id
                assert "youtube.com/watch" in item.url
