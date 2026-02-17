from pydantic import BaseModel


class DocInfo(BaseModel):
    id: str
    title: str
    url: str


class DocContent(BaseModel):
    id: str
    title: str
    body_text: str
    url: str


class CreateDocRequest(BaseModel):
    title: str


class InsertTextRequest(BaseModel):
    text: str
    index: int = 1


class ReplaceTextRequest(BaseModel):
    find: str
    replace_with: str
    match_case: bool = True
