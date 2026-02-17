import pytest
from unittest.mock import MagicMock, patch

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.gmail import GmailMessage

SAMPLE_MSG = GmailMessage(
    id="msg123", thread_id="t1", subject="Hi", from_addr="a@b.com",
    to_addr="c@d.com", date="Mon, 1 Jan 2025", snippet="hello", body="body",
)


@pytest.fixture
def client(mocker):
    mocker.patch("brokenclaw.routers.gmail.gmail_service")
    from brokenclaw.main import api
    from fastapi.testclient import TestClient
    return TestClient(api)


@pytest.fixture
def mock_svc(mocker):
    return mocker.patch("brokenclaw.routers.gmail.gmail_service")


class TestInbox:
    def test_returns_inbox(self, client, mock_svc):
        mock_svc.get_inbox.return_value = [SAMPLE_MSG]
        resp = client.get("/api/gmail/inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result_count"] == 1
        assert data["messages"][0]["id"] == "msg123"

    def test_forwards_params(self, client, mock_svc):
        mock_svc.get_inbox.return_value = []
        client.get("/api/gmail/inbox?max_results=5&account=school")
        mock_svc.get_inbox.assert_called_once_with(5, account="school")


class TestSearch:
    def test_returns_results(self, client, mock_svc):
        mock_svc.search_messages.return_value = [SAMPLE_MSG]
        resp = client.get("/api/gmail/search?query=from:alice")
        assert resp.status_code == 200
        assert resp.json()["result_count"] == 1

    def test_forwards_params(self, client, mock_svc):
        mock_svc.search_messages.return_value = []
        client.get("/api/gmail/search?query=test&max_results=3&account=work")
        mock_svc.search_messages.assert_called_once_with("test", 3, account="work")


class TestGetMessage:
    def test_returns_message(self, client, mock_svc):
        mock_svc.get_message.return_value = SAMPLE_MSG
        resp = client.get("/api/gmail/messages/msg123")
        assert resp.status_code == 200
        assert resp.json()["id"] == "msg123"


class TestSend:
    def test_sends_message(self, client, mock_svc):
        mock_svc.send_message.return_value = SAMPLE_MSG
        resp = client.post("/api/gmail/send", json={"to": "x@y.com", "subject": "Hi", "body": "Hello"})
        assert resp.status_code == 200

    def test_forwards_account(self, client, mock_svc):
        mock_svc.send_message.return_value = SAMPLE_MSG
        client.post("/api/gmail/send?account=school", json={"to": "x@y.com", "subject": "Hi", "body": "Hello"})
        mock_svc.send_message.assert_called_once_with("x@y.com", "Hi", "Hello", account="school")


class TestReply:
    def test_replies(self, client, mock_svc):
        mock_svc.reply_to_message.return_value = SAMPLE_MSG
        resp = client.post("/api/gmail/messages/msg123/reply", json={"body": "Thanks"})
        assert resp.status_code == 200


class TestExceptionMapping:
    def test_auth_error_returns_401(self, client, mock_svc):
        mock_svc.get_inbox.side_effect = AuthenticationError("Not authenticated")
        resp = client.get("/api/gmail/inbox")
        assert resp.status_code == 401

    def test_rate_limit_returns_429(self, client, mock_svc):
        mock_svc.get_inbox.side_effect = RateLimitError("Rate limited")
        resp = client.get("/api/gmail/inbox")
        assert resp.status_code == 429

    def test_integration_error_returns_500(self, client, mock_svc):
        mock_svc.get_inbox.side_effect = IntegrationError("API failed")
        resp = client.get("/api/gmail/inbox")
        assert resp.status_code == 500
