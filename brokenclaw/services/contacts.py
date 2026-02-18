from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_contacts_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.contacts import ContactInfo

PERSON_FIELDS = "names,emailAddresses,phoneNumbers,organizations"


def _get_people_service(account: str = "default"):
    try:
        creds = get_contacts_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Contacts credentials: {e}. Visit /auth/contacts/setup?account={account}."
        ) from e
    return build("people", "v1", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("People API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Contacts credentials expired or revoked. Visit /auth/contacts/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"People API error: {e}") from e


def _parse_contact(person: dict) -> ContactInfo:
    names = person.get("names", [])
    name = names[0] if names else {}
    emails = [e.get("value", "") for e in person.get("emailAddresses", []) if e.get("value")]
    phones = [p.get("value", "") for p in person.get("phoneNumbers", []) if p.get("value")]
    orgs = person.get("organizations", [])
    org = orgs[0] if orgs else {}
    return ContactInfo(
        resource_name=person.get("resourceName", ""),
        display_name=name.get("displayName"),
        given_name=name.get("givenName"),
        family_name=name.get("familyName"),
        emails=emails,
        phones=phones,
        organization=org.get("name"),
        title=org.get("title"),
    )


def list_contacts(max_results: int = 50, account: str = "default") -> list[ContactInfo]:
    """List the user's contacts."""
    service = _get_people_service(account)
    try:
        result = service.people().connections().list(
            resourceName="people/me",
            pageSize=min(max_results, 1000),
            personFields=PERSON_FIELDS,
            sortOrder="LAST_MODIFIED_DESCENDING",
        ).execute()
        return [_parse_contact(p) for p in result.get("connections", [])]
    except HttpError as e:
        _handle_api_error(e)


def search_contacts(query: str, max_results: int = 10, account: str = "default") -> list[ContactInfo]:
    """Search contacts by name, email, phone, or organization."""
    service = _get_people_service(account)
    try:
        # Warmup request (recommended by API docs)
        service.people().searchContacts(
            query="",
            readMask=PERSON_FIELDS,
            pageSize=1,
        ).execute()
        result = service.people().searchContacts(
            query=query,
            readMask=PERSON_FIELDS,
            pageSize=min(max_results, 30),
        ).execute()
        contacts = []
        for item in result.get("results", []):
            person = item.get("person", {})
            if person:
                contacts.append(_parse_contact(person))
        return contacts
    except HttpError as e:
        _handle_api_error(e)


def get_contact(resource_name: str, account: str = "default") -> ContactInfo:
    """Get a specific contact by resource name (e.g. 'people/c12345')."""
    service = _get_people_service(account)
    try:
        person = service.people().get(
            resourceName=resource_name,
            personFields=PERSON_FIELDS,
        ).execute()
        return _parse_contact(person)
    except HttpError as e:
        _handle_api_error(e)


def create_contact(
    given_name: str,
    family_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    organization: str | None = None,
    title: str | None = None,
    account: str = "default",
) -> ContactInfo:
    """Create a new contact."""
    service = _get_people_service(account)
    try:
        body = {
            "names": [{"givenName": given_name}],
        }
        if family_name:
            body["names"][0]["familyName"] = family_name
        if email:
            body["emailAddresses"] = [{"value": email}]
        if phone:
            body["phoneNumbers"] = [{"value": phone}]
        if organization or title:
            org = {}
            if organization:
                org["name"] = organization
            if title:
                org["title"] = title
            body["organizations"] = [org]
        person = service.people().createContact(body=body).execute()
        return _parse_contact(person)
    except HttpError as e:
        _handle_api_error(e)


def update_contact(
    resource_name: str,
    given_name: str | None = None,
    family_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    organization: str | None = None,
    title: str | None = None,
    account: str = "default",
) -> ContactInfo:
    """Update an existing contact. Only provided fields are changed."""
    service = _get_people_service(account)
    try:
        existing = service.people().get(
            resourceName=resource_name,
            personFields=PERSON_FIELDS,
        ).execute()
        update_fields = []
        if given_name is not None or family_name is not None:
            names = existing.get("names", [{}])
            name = names[0] if names else {}
            if given_name is not None:
                name["givenName"] = given_name
            if family_name is not None:
                name["familyName"] = family_name
            existing["names"] = [name]
            update_fields.append("names")
        if email is not None:
            existing["emailAddresses"] = [{"value": email}]
            update_fields.append("emailAddresses")
        if phone is not None:
            existing["phoneNumbers"] = [{"value": phone}]
            update_fields.append("phoneNumbers")
        if organization is not None or title is not None:
            orgs = existing.get("organizations", [{}])
            org = orgs[0] if orgs else {}
            if organization is not None:
                org["name"] = organization
            if title is not None:
                org["title"] = title
            existing["organizations"] = [org]
            update_fields.append("organizations")
        if not update_fields:
            return _parse_contact(existing)
        person = service.people().updateContact(
            resourceName=resource_name,
            body=existing,
            updatePersonFields=",".join(update_fields),
        ).execute()
        return _parse_contact(person)
    except HttpError as e:
        _handle_api_error(e)


def delete_contact(resource_name: str, account: str = "default") -> None:
    """Delete a contact."""
    service = _get_people_service(account)
    try:
        service.people().deleteContact(resourceName=resource_name).execute()
    except HttpError as e:
        _handle_api_error(e)
