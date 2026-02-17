import pytest
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.gmail import GmailMessage
from brokenclaw.services import gmail as gmail_service
from conftest import GMAIL_API_LIST, GMAIL_API_MESSAGE, GMAIL_API_SEND


def _setup_list_and_get(mock_svc, list_response=GMAIL_API_LIST, get_response=GMAIL_API_MESSAGE):
    """Configure mock for list + get pattern used by inbox/search."""
    mock_svc.users().messages().list().execute.return_value = list_response
    mock_svc.users().messages().get().execute.return_value = get_response


class TestGetInbox:
    def test_returns_list_of_gmail_messages(self, mock_gmail_service):
        _setup_list_and_get(mock_gmail_service)
        result = gmail_service.get_inbox(max_results=5)
        assert len(result) == 1
        assert isinstance(result[0], GmailMessage)
        assert result[0].id == "msg123"
        assert result[0].subject == "Hello"
        assert result[0].from_addr == "alice@example.com"

    def test_empty_inbox(self, mock_gmail_service):
        _setup_list_and_get(mock_gmail_service, list_response={"messages": []})
        result = gmail_service.get_inbox()
        assert result == []

    def test_no_messages_key(self, mock_gmail_service):
        _setup_list_and_get(mock_gmail_service, list_response={})
        result = gmail_service.get_inbox()
        assert result == []

    def test_forwards_account(self, mock_gmail_credentials, mock_gmail_build):
        _setup_list_and_get(mock_gmail_build, list_response={})
        gmail_service.get_inbox(account="school")
        mock_gmail_credentials.assert_called_with("school")


class TestSearchMessages:
    def test_returns_matching_messages(self, mock_gmail_service):
        _setup_list_and_get(mock_gmail_service)
        result = gmail_service.search_messages("from:alice")
        assert len(result) == 1
        assert result[0].from_addr == "alice@example.com"

    def test_empty_results(self, mock_gmail_service):
        _setup_list_and_get(mock_gmail_service, list_response={})
        result = gmail_service.search_messages("nonexistent")
        assert result == []


class TestGetMessage:
    def test_returns_single_message(self, mock_gmail_service):
        mock_gmail_service.users().messages().get().execute.return_value = GMAIL_API_MESSAGE
        result = gmail_service.get_message("msg123")
        assert isinstance(result, GmailMessage)
        assert result.id == "msg123"
        assert result.body == "Hello world"

    def test_message_without_body(self, mock_gmail_service):
        msg = {**GMAIL_API_MESSAGE, "payload": {**GMAIL_API_MESSAGE["payload"], "body": {}, "mimeType": "multipart/mixed", "parts": []}}
        mock_gmail_service.users().messages().get().execute.return_value = msg
        result = gmail_service.get_message("msg123")
        assert result.body is None


class TestSendMessage:
    def test_sends_and_returns_message(self, mock_gmail_service):
        mock_gmail_service.users().messages().send().execute.return_value = GMAIL_API_SEND
        mock_gmail_service.users().messages().get().execute.return_value = GMAIL_API_MESSAGE
        result = gmail_service.send_message("bob@example.com", "Hi", "Hello there")
        assert isinstance(result, GmailMessage)
        assert result.id == "msg123"


class TestReplyToMessage:
    def test_replies_in_thread(self, mock_gmail_service):
        mock_gmail_service.users().messages().get().execute.return_value = GMAIL_API_MESSAGE
        mock_gmail_service.users().messages().send().execute.return_value = GMAIL_API_SEND
        result = gmail_service.reply_to_message("msg123", "Thanks!")
        assert isinstance(result, GmailMessage)


class TestErrorHandling:
    def _make_http_error(self, status):
        resp = MagicMock()
        resp.status = status
        return HttpError(resp=resp, content=b"error")

    def test_401_raises_auth_error(self, mock_gmail_service):
        mock_gmail_service.users().messages().list().execute.side_effect = self._make_http_error(401)
        with pytest.raises(AuthenticationError):
            gmail_service.get_inbox()

    def test_429_raises_rate_limit(self, mock_gmail_service):
        mock_gmail_service.users().messages().list().execute.side_effect = self._make_http_error(429)
        with pytest.raises(RateLimitError):
            gmail_service.get_inbox()

    def test_500_raises_integration_error(self, mock_gmail_service):
        mock_gmail_service.users().messages().list().execute.side_effect = self._make_http_error(500)
        with pytest.raises(IntegrationError):
            gmail_service.get_inbox()

    def test_missing_credentials_raises_auth_error(self, mocker):
        mocker.patch("brokenclaw.services.gmail.get_gmail_credentials", side_effect=RuntimeError("Not authenticated"))
        with pytest.raises(AuthenticationError):
            gmail_service.get_inbox()
