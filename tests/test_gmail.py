import pytest

from brokenclaw.models.gmail import GmailMessage
from brokenclaw.services import gmail as gmail_service
from brokenclaw.services.gmail import _get_gmail_service
from tests.conftest import requires_gmail


@requires_gmail
class TestGetInbox:
    def test_returns_list_of_messages(self):
        messages = gmail_service.get_inbox(max_results=3)
        assert isinstance(messages, list)
        assert len(messages) <= 3
        if messages:
            msg = messages[0]
            assert isinstance(msg, GmailMessage)
            assert msg.id
            assert msg.subject is not None
            assert msg.from_addr

    def test_respects_max_results(self):
        messages = gmail_service.get_inbox(max_results=1)
        assert len(messages) <= 1


@requires_gmail
class TestSearchMessages:
    def test_search_returns_results(self):
        # Search for anything — inbox should have at least one message
        messages = gmail_service.search_messages("in:inbox", max_results=2)
        assert isinstance(messages, list)

    def test_search_with_no_matches(self):
        messages = gmail_service.search_messages("from:zzznonexistent9999@nowhere.invalid", max_results=5)
        assert messages == []


@requires_gmail
class TestGetMessage:
    def test_get_real_message(self):
        # Get an inbox message, then fetch it by ID
        inbox = gmail_service.get_inbox(max_results=1)
        if not inbox:
            pytest.skip("Inbox is empty")
        msg = gmail_service.get_message(inbox[0].id)
        assert isinstance(msg, GmailMessage)
        assert msg.id == inbox[0].id
        assert msg.subject == inbox[0].subject


@requires_gmail
class TestSendAndReply:
    def _cleanup_message(self, message_id: str):
        """Trash the sent message to keep mailbox clean."""
        service = _get_gmail_service()
        service.users().messages().trash(userId="me", id=message_id).execute()

    def test_send_message_to_self(self):
        # Get our own email address
        service = _get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        my_email = profile["emailAddress"]

        sent = gmail_service.send_message(
            to=my_email,
            subject="[Brokenclaw Test] Send test — safe to delete",
            body="Automated test from brokenclaw test suite.",
        )
        assert isinstance(sent, GmailMessage)
        assert sent.id
        self._cleanup_message(sent.id)

    def test_reply_to_message(self):
        inbox = gmail_service.get_inbox(max_results=1)
        if not inbox:
            pytest.skip("Inbox is empty")

        reply = gmail_service.reply_to_message(
            message_id=inbox[0].id,
            body="[Brokenclaw Test] Reply test — safe to delete",
        )
        assert isinstance(reply, GmailMessage)
        assert reply.thread_id == inbox[0].thread_id
        self._cleanup_message(reply.id)
