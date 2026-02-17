from pydantic import BaseModel


class FormInfo(BaseModel):
    id: str
    title: str
    description: str | None = None
    responder_uri: str | None = None
    url: str


class FormQuestion(BaseModel):
    item_id: str
    title: str
    description: str | None = None
    question_type: str  # TEXT, PARAGRAPH, RADIO, CHECKBOX, DROP_DOWN, SCALE, etc.


class FormDetail(BaseModel):
    id: str
    title: str
    description: str | None = None
    questions: list[FormQuestion]
    responder_uri: str | None = None
    url: str


class FormResponseAnswer(BaseModel):
    question_id: str
    text_answers: list[str] | None = None


class FormResponseInfo(BaseModel):
    response_id: str
    create_time: str | None = None
    last_submitted_time: str | None = None
    answers: list[FormResponseAnswer]


class CreateFormRequest(BaseModel):
    title: str


class AddQuestionRequest(BaseModel):
    title: str
    question_type: str = "TEXT"  # TEXT, PARAGRAPH, RADIO, CHECKBOX, DROP_DOWN
    options: list[str] | None = None  # Required for RADIO, CHECKBOX, DROP_DOWN
    required: bool = False
