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
from brokenclaw.services import instagram as instagram_service
from tests.conftest import requires_instagram_session


@requires_instagram_session
class TestProfile:
    def test_my_profile_returns_model(self):
        result = instagram_service.get_my_profile()
        assert isinstance(result, InstagramProfile)
        assert result.username

    def test_my_profile_has_user_id(self):
        result = instagram_service.get_my_profile()
        assert result.user_id


@requires_instagram_session
class TestFeed:
    def test_feed_returns_list(self):
        posts = instagram_service.get_my_feed(count=5)
        assert isinstance(posts, list)
        for post in posts:
            assert isinstance(post, InstagramPost)

    def test_feed_posts_have_ids(self):
        posts = instagram_service.get_my_feed(count=5)
        for post in posts:
            assert post.post_id


@requires_instagram_session
class TestPosts:
    def test_user_posts_returns_list(self):
        profile = instagram_service.get_my_profile()
        posts = instagram_service.get_user_posts(profile.user_id, count=5)
        assert isinstance(posts, list)
        for post in posts:
            assert isinstance(post, InstagramPost)


@requires_instagram_session
class TestStories:
    def test_stories_tray_returns_list(self):
        stories = instagram_service.get_my_stories()
        assert isinstance(stories, list)
        for story in stories:
            assert isinstance(story, InstagramStory)


@requires_instagram_session
class TestReels:
    def test_user_reels_returns_list(self):
        profile = instagram_service.get_my_profile()
        reels = instagram_service.get_user_reels(profile.user_id, count=5)
        assert isinstance(reels, list)
        for reel in reels:
            assert isinstance(reel, InstagramReel)


@requires_instagram_session
class TestFollowers:
    def test_followers_returns_list(self):
        profile = instagram_service.get_my_profile()
        followers = instagram_service.list_followers(profile.user_id, count=5)
        assert isinstance(followers, list)
        for f in followers:
            assert isinstance(f, InstagramFollower)

    def test_following_returns_list(self):
        profile = instagram_service.get_my_profile()
        following = instagram_service.list_following(profile.user_id, count=5)
        assert isinstance(following, list)
        for f in following:
            assert isinstance(f, InstagramFollower)


@requires_instagram_session
class TestSaved:
    def test_saved_returns_list(self):
        saved = instagram_service.get_saved_posts(count=5)
        assert isinstance(saved, list)
        for post in saved:
            assert isinstance(post, InstagramSavedPost)


@requires_instagram_session
class TestDirect:
    def test_direct_returns_list(self):
        threads = instagram_service.list_direct_threads(count=5)
        assert isinstance(threads, list)
        for thread in threads:
            assert isinstance(thread, InstagramDirectThread)


@requires_instagram_session
class TestSearch:
    def test_search_users(self):
        results = instagram_service.search_users("instagram", count=5)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, InstagramSearchResult)
