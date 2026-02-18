from brokenclaw.models.contacts import ContactInfo
from brokenclaw.services import contacts as contacts_service
from tests.conftest import requires_contacts


@requires_contacts
class TestListContacts:
    def test_returns_list(self):
        contacts = contacts_service.list_contacts(max_results=5)
        assert isinstance(contacts, list)
        for c in contacts:
            assert isinstance(c, ContactInfo)
            assert c.resource_name


@requires_contacts
class TestSearchContacts:
    def test_search(self):
        # Search for a common name - may return 0 results if contacts list is small
        contacts = contacts_service.search_contacts("test", max_results=5)
        assert isinstance(contacts, list)
        for c in contacts:
            assert isinstance(c, ContactInfo)


@requires_contacts
class TestCreateUpdateDeleteContact:
    def test_full_lifecycle(self):
        created = contacts_service.create_contact(
            given_name="Brokenclaw",
            family_name="TestContact",
            email="brokenclaw_test@example.com",
            phone="+15551234567",
            organization="Test Corp",
            title="QA Engineer",
        )
        try:
            assert isinstance(created, ContactInfo)
            assert created.resource_name
            assert created.given_name == "Brokenclaw"
            assert created.family_name == "TestContact"
            assert "brokenclaw_test@example.com" in created.emails
            assert "+15551234567" in [p.replace(" ", "") for p in created.phones]
            assert created.organization == "Test Corp"
            assert created.title == "QA Engineer"

            # Get the contact
            fetched = contacts_service.get_contact(created.resource_name)
            assert fetched.resource_name == created.resource_name
            assert fetched.given_name == "Brokenclaw"

            # Update the contact
            updated = contacts_service.update_contact(
                created.resource_name,
                given_name="BrokenclawUpdated",
            )
            assert updated.given_name == "BrokenclawUpdated"
        finally:
            contacts_service.delete_contact(created.resource_name)
