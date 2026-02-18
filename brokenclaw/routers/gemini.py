from fastapi import APIRouter
from pydantic import BaseModel

from brokenclaw.models.gemini import GeminiAnalysis
from brokenclaw.services import gemini as gemini_service

router = APIRouter(prefix="/api/gemini", tags=["gemini"])


class AnalyzeRequest(BaseModel):
    url: str
    prompt: str = "Describe this media in detail."
    platform: str | None = None
    account: str = "default"
    model: str = "gemini-2.5-flash"


@router.post("/analyze")
def analyze(req: AnalyzeRequest) -> GeminiAnalysis:
    return gemini_service.analyze_url(
        url=req.url,
        prompt=req.prompt,
        platform=req.platform,
        account=req.account,
        model=req.model,
    )
