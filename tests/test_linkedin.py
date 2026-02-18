from brokenclaw.models.linkedin import (
    LinkedInConnection,
    LinkedInConversation,
    LinkedInFullProfile,
    LinkedInMessage,
    LinkedInNotification,
    LinkedInPost,
    LinkedInProfile,
    LinkedInSearchResult,
)
from brokenclaw.services import linkedin as linkedin_service
from tests.conftest import requires_linkedin_session


@requires_linkedin_session
class TestProfile:
    def test_my_profile_returns_model(self):
        result = linkedin_service.get_my_profile()
        assert isinstance(result, LinkedInProfile)
        assert result.first_name

    def test_my_profile_has_url(self):
        result = linkedin_service.get_my_profile()
        assert result.profile_url is None or result.profile_url.startswith("https://www.linkedin.com/in/")


@requires_linkedin_session
class TestFeed:
    def test_feed_returns_list(self):
        posts = linkedin_service.get_feed(count=5)
        assert isinstance(posts, list)
        for post in posts:
            assert isinstance(post, LinkedInPost)

    def test_feed_posts_have_text(self):
        posts = linkedin_service.get_feed(count=5)
        for post in posts:
            assert post.text


@requires_linkedin_session
class TestConnections:
    def test_connections_returns_list(self):
        conns = linkedin_service.list_connections(count=5)
        assert isinstance(conns, list)
        for conn in conns:
            assert isinstance(conn, LinkedInConnection)

    def test_connections_have_names(self):
        conns = linkedin_service.list_connections(count=5)
        for conn in conns:
            assert conn.first_name or conn.last_name


@requires_linkedin_session
class TestConversations:
    def test_conversations_returns_list(self):
        convos = linkedin_service.list_conversations(count=5)
        assert isinstance(convos, list)
        for convo in convos:
            assert isinstance(convo, LinkedInConversation)


@requires_linkedin_session
class TestNotifications:
    def test_notifications_returns_list(self):
        notifs = linkedin_service.list_notifications(count=5)
        assert isinstance(notifs, list)
        for notif in notifs:
            assert isinstance(notif, LinkedInNotification)


@requires_linkedin_session
class TestSearch:
    def test_search_people(self):
        results = linkedin_service.search_people("software engineer", count=3)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, LinkedInSearchResult)

    def test_search_companies(self):
        results = linkedin_service.search_companies("Google", count=3)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, LinkedInSearchResult)

    def test_search_jobs(self):
        results = linkedin_service.search_jobs("python developer", count=3)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, LinkedInSearchResult)
