from brokenclaw.models.slack import (
    SlackChannel,
    SlackMessage,
    SlackPostResult,
    SlackSearchResult,
    SlackUser,
)
from brokenclaw.services import slack as slack_service
from tests.conftest import requires_slack


@requires_slack
class TestListChannels:
    def test_returns_list(self):
        channels = slack_service.list_channels(max_results=10)
        assert isinstance(channels, list)
        assert len(channels) > 0
        ch = channels[0]
        assert isinstance(ch, SlackChannel)
        assert ch.id
        assert ch.name


@requires_slack
class TestListUsers:
    def test_returns_list(self):
        users = slack_service.list_users(max_results=10)
        assert isinstance(users, list)
        assert len(users) > 0
        user = users[0]
        assert isinstance(user, SlackUser)
        assert user.id
        assert user.name


@requires_slack
class TestChannelHistory:
    def test_read_history(self):
        # Get first channel and read its history
        channels = slack_service.list_channels(max_results=1)
        assert len(channels) > 0
        messages = slack_service.get_channel_history(channels[0].id, max_results=5)
        assert isinstance(messages, list)
        for msg in messages:
            assert isinstance(msg, SlackMessage)
            assert msg.ts


@requires_slack
class TestSearchMessages:
    def test_search(self):
        result = slack_service.search_messages("hello", max_results=5)
        assert isinstance(result, SlackSearchResult)
        assert result.query == "hello"
        assert isinstance(result.total, int)
        assert isinstance(result.messages, list)


@requires_slack
class TestSendMessage:
    def test_send_and_react(self):
        # Find a channel to post in — use the first available
        channels = slack_service.list_channels(max_results=10)
        # Look for a test or general channel
        target = None
        for ch in channels:
            if "test" in ch.name.lower() or "bot" in ch.name.lower():
                target = ch
                break
        if not target:
            target = channels[0]

        result = slack_service.send_message(target.id, "brokenclaw integration test - please ignore")
        assert isinstance(result, SlackPostResult)
        assert result.ok
        assert result.ts

        # Add a reaction to the message we just sent
        reaction = slack_service.add_reaction(target.id, result.ts, "white_check_mark")
        assert reaction["ok"]
