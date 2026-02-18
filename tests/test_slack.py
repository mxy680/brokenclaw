from brokenclaw.models.slack import (
    SlackConversation,
    SlackMessage,
    SlackProfile,
    SlackSearchResult,
)
from brokenclaw.services import slack as slack_service
from tests.conftest import requires_slack_session


@requires_slack_session
class TestProfile:
    def test_my_profile_returns_model(self):
        result = slack_service.get_my_profile()
        assert isinstance(result, SlackProfile)
        assert result.user_id

    def test_my_profile_has_username(self):
        result = slack_service.get_my_profile()
        assert result.username


@requires_slack_session
class TestConversations:
    def test_list_conversations_returns_list(self):
        convos = slack_service.list_conversations(count=10)
        assert isinstance(convos, list)
        for c in convos:
            assert isinstance(c, SlackConversation)
            assert c.channel_id

    def test_list_dms_only(self):
        convos = slack_service.list_conversations(types="im", count=5)
        assert isinstance(convos, list)
        for c in convos:
            assert isinstance(c, SlackConversation)


@requires_slack_session
class TestMessages:
    def test_get_messages_returns_list(self):
        convos = slack_service.list_conversations(count=1)
        if convos:
            msgs = slack_service.get_messages(convos[0].channel_id, count=5)
            assert isinstance(msgs, list)
            for m in msgs:
                assert isinstance(m, SlackMessage)


@requires_slack_session
class TestSearch:
    def test_search_returns_list(self):
        results = slack_service.search_messages("hello", count=5)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, SlackSearchResult)


@requires_slack_session
class TestUsers:
    def test_list_users_returns_list(self):
        users = slack_service.list_users(count=10)
        assert isinstance(users, list)
        for u in users:
            assert isinstance(u, SlackProfile)
            assert u.user_id
