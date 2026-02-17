from fastapi import APIRouter

from brokenclaw.models.slides import (
    AddSlideRequest,
    CreatePresentationRequest,
    PresentationContent,
    PresentationInfo,
    ReplaceTextRequest,
)
from brokenclaw.services import slides as slides_service

router = APIRouter(prefix="/api/slides", tags=["slides"])


@router.get("/presentations/{presentation_id}")
def get_presentation(presentation_id: str, account: str = "default") -> PresentationInfo:
    return slides_service.get_presentation(presentation_id, account=account)


@router.get("/presentations/{presentation_id}/content")
def get_presentation_content(presentation_id: str, account: str = "default") -> PresentationContent:
    return slides_service.get_presentation_content(presentation_id, account=account)


@router.post("/presentations")
def create_presentation(request: CreatePresentationRequest, account: str = "default") -> PresentationInfo:
    return slides_service.create_presentation(request.title, account=account)


@router.post("/presentations/{presentation_id}/slides")
def add_slide(presentation_id: str, request: AddSlideRequest, account: str = "default") -> PresentationInfo:
    return slides_service.add_slide(presentation_id, request.layout, account=account)


@router.post("/presentations/{presentation_id}/replace")
def replace_text(presentation_id: str, request: ReplaceTextRequest, account: str = "default") -> PresentationInfo:
    return slides_service.replace_text(presentation_id, request.find, request.replace_with, request.match_case, account=account)
