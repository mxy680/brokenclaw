from fastapi import APIRouter

from brokenclaw.models.canvas import CanvasUpcoming
from brokenclaw.services import canvas as canvas_service

router = APIRouter(prefix="/api/canvas", tags=["canvas"])


@router.get("/upcoming")
def upcoming(days: int = 14) -> CanvasUpcoming:
    return canvas_service.get_upcoming(days)


@router.get("/events")
def all_events() -> CanvasUpcoming:
    return canvas_service.get_all_events()
