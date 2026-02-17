from fastapi import APIRouter

from brokenclaw.models.docs import (
    CreateDocRequest,
    DocContent,
    DocInfo,
    InsertTextRequest,
    ReplaceTextRequest,
)
from brokenclaw.services import docs as docs_service

router = APIRouter(prefix="/api/docs", tags=["docs"])


@router.get("/documents/{document_id}")
def get_document(document_id: str, account: str = "default") -> DocInfo:
    return docs_service.get_document(document_id, account=account)


@router.get("/documents/{document_id}/content")
def get_document_content(document_id: str, account: str = "default") -> DocContent:
    return docs_service.get_document_content(document_id, account=account)


@router.post("/documents")
def create_document(request: CreateDocRequest, account: str = "default") -> DocInfo:
    return docs_service.create_document(request.title, account=account)


@router.post("/documents/{document_id}/insert")
def insert_text(document_id: str, request: InsertTextRequest, account: str = "default") -> DocInfo:
    return docs_service.insert_text(document_id, request.text, request.index, account=account)


@router.post("/documents/{document_id}/replace")
def replace_text(document_id: str, request: ReplaceTextRequest, account: str = "default") -> DocInfo:
    return docs_service.replace_text(document_id, request.find, request.replace_with, request.match_case, account=account)
