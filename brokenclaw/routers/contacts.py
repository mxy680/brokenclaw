from fastapi import APIRouter

from brokenclaw.models.contacts import ContactInfo
from brokenclaw.services import contacts as contacts_service

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("/")
def list_contacts(max_results: int = 50, account: str = "default") -> list[ContactInfo]:
    return contacts_service.list_contacts(max_results, account=account)


@router.get("/search")
def search_contacts(query: str, max_results: int = 10, account: str = "default") -> list[ContactInfo]:
    return contacts_service.search_contacts(query, max_results, account=account)


@router.get("/{resource_name}")
def get_contact(resource_name: str, account: str = "default") -> ContactInfo:
    return contacts_service.get_contact(resource_name, account=account)


@router.post("/")
def create_contact(
    given_name: str,
    family_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    organization: str | None = None,
    title: str | None = None,
    account: str = "default",
) -> ContactInfo:
    return contacts_service.create_contact(
        given_name, family_name, email, phone, organization, title, account=account,
    )


@router.put("/{resource_name}")
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
    return contacts_service.update_contact(
        resource_name, given_name, family_name, email, phone, organization, title, account=account,
    )


@router.delete("/{resource_name}")
def delete_contact(resource_name: str, account: str = "default"):
    contacts_service.delete_contact(resource_name, account=account)
    return {"status": "deleted", "resource_name": resource_name}
