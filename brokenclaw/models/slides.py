from pydantic import BaseModel


class PresentationInfo(BaseModel):
    id: str
    title: str
    slides_count: int
    url: str


class PresentationContent(BaseModel):
    id: str
    title: str
    slides_count: int
    slides_text: list[str]
    url: str


class CreatePresentationRequest(BaseModel):
    title: str


class AddSlideRequest(BaseModel):
    layout: str = "BLANK"


class ReplaceTextRequest(BaseModel):
    find: str
    replace_with: str
    match_case: bool = True
