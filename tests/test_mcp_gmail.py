import pytest
from unittest.mock import MagicMock

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.gmail import GmailMessage

SAMPLE_MSG = GmailMessage(
    id="msg123", thread_id="t1", subject="Hi", from_addr="a@b.com",
    to_addr="c@d.com", date="Mon, 1 Jan 2025", snippet="hello", body="body",
)


@pytest.fixture(autouse=True)
def mock_svc(mocker):
    return mocker.patch("brokenclaw.mcp_server.gmail_service")


@pytest.fixture(autouse=True)
def mock_store(mocker):
    store = MagicMock()
    store.list_accounts.return_value = ["default"]
    mocker.patch("brokenclaw.mcp_server._get_token_store", return_value=store)
    return store


class TestGmailInbox:
    def test_returns_dict(self, mock_svc):
        mock_svc.get_inbox.return_value = [SAMPLE_MSG]
        from brokenclaw.mcp_server import gmail_inbox
        result = gmail_inbox.fn(max_results=5)
        assert isinstance(result, dict)
        assert result["count"] == 1
        assert result["messages"][0]["id"] == "msg123"

    def test_forwards_account(self, mock_svc):
        mock_svc.get_inbox.return_value = []
        from brokenclaw.mcp_server import gmail_inbox
        gmail_inbox.fn(account="school")
        mock_svc.get_inbox.assert_called_once_with(20, account="school")

    def test_error_returns_dict_not_raises(self, mock_svc):
        mock_svc.get_inbox.side_effect = AuthenticationError("Not auth")
        from brokenclaw.mcp_server import gmail_inbox
        result = gmail_inbox.fn()
        assert isinstance(result, dict)
        assert result["error"] == "auth_error"
        assert "Not auth" in result["message"]


class TestGmailSearch:
    def test_returns_dict(self, mock_svc):
        mock_svc.search_messages.return_value = [SAMPLE_MSG]
        from brokenclaw.mcp_server import gmail_search
        result = gmail_search.fn(query="from:alice")
        assert result["count"] == 1

    def test_error_returns_dict(self, mock_svc):
        mock_svc.search_messages.side_effect = RateLimitError("Slow down")
        from brokenclaw.mcp_server import gmail_search
        result = gmail_search.fn(query="test")
        assert result["error"] == "rate_limit"


class TestGmailGetMessage:
    def test_returns_dict(self, mock_svc):
        mock_svc.get_message.return_value = SAMPLE_MSG
        from brokenclaw.mcp_server import gmail_get_message
        result = gmail_get_message.fn(message_id="msg123")
        assert isinstance(result, dict)
        assert result["id"] == "msg123"


class TestGmailSend:
    def test_returns_dict(self, mock_svc):
        mock_svc.send_message.return_value = SAMPLE_MSG
        from brokenclaw.mcp_server import gmail_send
        result = gmail_send.fn(to="x@y.com", subject="Hi", body="Hello")
        assert isinstance(result, dict)

    def test_error_returns_dict(self, mock_svc):
        mock_svc.send_message.side_effect = IntegrationError("API error")
        from brokenclaw.mcp_server import gmail_send
        result = gmail_send.fn(to="x@y.com", subject="Hi", body="Hello")
        assert result["error"] == "integration_error"


class TestGmailReply:
    def test_returns_dict(self, mock_svc):
        mock_svc.reply_to_message.return_value = SAMPLE_MSG
        from brokenclaw.mcp_server import gmail_reply
        result = gmail_reply.fn(message_id="msg123", body="Thanks")
        assert isinstance(result, dict)
