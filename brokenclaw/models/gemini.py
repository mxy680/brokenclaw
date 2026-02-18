from pydantic import BaseModel


class GeminiAnalysis(BaseModel):
    analysis: str
    model: str
    media_type: str  # "image" or "video"
