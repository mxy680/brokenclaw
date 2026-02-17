from fastapi import APIRouter

from brokenclaw.models.sheets import (
    AppendRequest,
    CreateSpreadsheetRequest,
    ReadRangeResponse,
    SpreadsheetInfo,
    WriteRangeRequest,
    WriteRangeResponse,
)
from brokenclaw.services import sheets as sheets_service

router = APIRouter(prefix="/api/sheets", tags=["sheets"])


@router.get("/spreadsheets/{spreadsheet_id}")
def get_spreadsheet(spreadsheet_id: str, account: str = "default") -> SpreadsheetInfo:
    return sheets_service.get_spreadsheet(spreadsheet_id, account=account)


@router.get("/spreadsheets/{spreadsheet_id}/values")
def read_range(spreadsheet_id: str, range: str, account: str = "default") -> ReadRangeResponse:
    return sheets_service.read_range(spreadsheet_id, range, account=account)


@router.post("/spreadsheets/{spreadsheet_id}/values")
def write_range(spreadsheet_id: str, request: WriteRangeRequest, account: str = "default") -> WriteRangeResponse:
    return sheets_service.write_range(spreadsheet_id, request.range, request.values, account=account)


@router.post("/spreadsheets/{spreadsheet_id}/append")
def append_rows(spreadsheet_id: str, request: AppendRequest, account: str = "default") -> WriteRangeResponse:
    return sheets_service.append_rows(spreadsheet_id, request.range, request.values, account=account)


@router.post("/spreadsheets")
def create_spreadsheet(request: CreateSpreadsheetRequest, account: str = "default") -> SpreadsheetInfo:
    return sheets_service.create_spreadsheet(request.title, request.sheet_names, account=account)
