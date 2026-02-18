from pydantic import BaseModel


class ContactInfo(BaseModel):
    resource_name: str
    display_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    emails: list[str] = []
    phones: list[str] = []
    organization: str | None = None
    title: str | None = None
