from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class StatusResponse(BaseModel):
    integration: str
    authenticated: bool
    message: str
