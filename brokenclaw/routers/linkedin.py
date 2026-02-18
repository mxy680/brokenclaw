import io

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from brokenclaw.models.linkedin import (
    LinkedInConnection,
    LinkedInConversation,
    LinkedInFullProfile,
    LinkedInMessage,
    LinkedInNotification,
    LinkedInPost,
    LinkedInProfile,
    LinkedInSearchResult,
)
from brokenclaw.services import linkedin as linkedin_service

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


@router.get("/media/download")
def download_media(url: str, account: str = "default"):
    data, filename, mime_type = linkedin_service.download_attachment(url, account)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/profile")
def profile(account: str = "default") -> LinkedInProfile:
    return linkedin_service.get_my_profile(account)


@router.get("/profile/full")
def full_profile(public_id: str, account: str = "default") -> LinkedInFullProfile:
    return linkedin_service.get_full_profile(public_id, account)


@router.get("/feed")
def feed(count: int = 20, account: str = "default") -> list[LinkedInPost]:
    return linkedin_service.get_feed(count, account)


@router.get("/connections")
def connections(count: int = 20, start: int = 0, account: str = "default") -> list[LinkedInConnection]:
    return linkedin_service.list_connections(count, start, account)


@router.get("/conversations")
def conversations(count: int = 20, account: str = "default") -> list[LinkedInConversation]:
    return linkedin_service.list_conversations(count, account)


@router.get("/conversations/{urn}/messages")
def conversation_messages(urn: str, count: int = 20, account: str = "default") -> list[LinkedInMessage]:
    return linkedin_service.get_conversation_messages(urn, count, account)


@router.get("/notifications")
def notifications(count: int = 20, account: str = "default") -> list[LinkedInNotification]:
    return linkedin_service.list_notifications(count, account)


@router.get("/search/people")
def search_people(keywords: str, count: int = 10, account: str = "default") -> list[LinkedInSearchResult]:
    return linkedin_service.search_people(keywords, count, account)


@router.get("/search/companies")
def search_companies(keywords: str, count: int = 10, account: str = "default") -> list[LinkedInSearchResult]:
    return linkedin_service.search_companies(keywords, count, account)


@router.get("/search/jobs")
def search_jobs(keywords: str, location: str | None = None, count: int = 10, account: str = "default") -> list[LinkedInSearchResult]:
    return linkedin_service.search_jobs(keywords, location, count, account)
