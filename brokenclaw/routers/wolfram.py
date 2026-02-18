from fastapi import APIRouter

from brokenclaw.models.wolfram import WolframResult, WolframShortAnswer
from brokenclaw.services import wolfram as wolfram_service

router = APIRouter(prefix="/api/wolfram", tags=["wolfram"])


@router.get("/query")
def query(input: str, units: str = "nonmetric") -> WolframResult:
    return wolfram_service.query(input, units)


@router.get("/short")
def short_answer(input: str, units: str = "imperial") -> WolframShortAnswer:
    return wolfram_service.short_answer(input, units)
