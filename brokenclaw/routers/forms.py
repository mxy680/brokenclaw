from fastapi import APIRouter

from brokenclaw.models.forms import (
    AddQuestionRequest,
    CreateFormRequest,
    FormDetail,
    FormInfo,
    FormResponseInfo,
)
from brokenclaw.services import forms as forms_service

router = APIRouter(prefix="/api/forms", tags=["forms"])


@router.get("/forms/{form_id}")
def get_form(form_id: str, account: str = "default") -> FormInfo:
    return forms_service.get_form(form_id, account=account)


@router.get("/forms/{form_id}/detail")
def get_form_detail(form_id: str, account: str = "default") -> FormDetail:
    return forms_service.get_form_detail(form_id, account=account)


@router.post("/forms")
def create_form(request: CreateFormRequest, account: str = "default") -> FormInfo:
    return forms_service.create_form(request.title, account=account)


@router.post("/forms/{form_id}/questions")
def add_question(form_id: str, request: AddQuestionRequest, account: str = "default") -> FormDetail:
    return forms_service.add_question(
        form_id, request.title, request.question_type, request.options, request.required, account=account,
    )


@router.get("/forms/{form_id}/responses")
def list_responses(form_id: str, max_results: int = 100, account: str = "default") -> list[FormResponseInfo]:
    return forms_service.list_responses(form_id, max_results, account=account)


@router.get("/forms/{form_id}/responses/{response_id}")
def get_response(form_id: str, response_id: str, account: str = "default") -> FormResponseInfo:
    return forms_service.get_response(form_id, response_id, account=account)
