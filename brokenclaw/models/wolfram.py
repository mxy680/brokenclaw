from pydantic import BaseModel


class WolframPod(BaseModel):
    title: str
    text: str | None = None


class WolframResult(BaseModel):
    input_interpretation: str | None = None
    pods: list[WolframPod]
    success: bool


class WolframShortAnswer(BaseModel):
    query: str
    answer: str
