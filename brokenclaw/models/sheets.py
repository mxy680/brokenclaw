from pydantic import BaseModel


class SpreadsheetInfo(BaseModel):
    id: str
    title: str
    sheets: list[str]
    url: str


class CellRange(BaseModel):
    range: str
    values: list[list[str]]


class ReadRangeResponse(BaseModel):
    spreadsheet_id: str
    range: str
    values: list[list[str]]


class WriteRangeRequest(BaseModel):
    range: str
    values: list[list[str]]


class WriteRangeResponse(BaseModel):
    spreadsheet_id: str
    updated_range: str
    updated_rows: int
    updated_columns: int
    updated_cells: int


class AppendRequest(BaseModel):
    range: str
    values: list[list[str]]


class CreateSpreadsheetRequest(BaseModel):
    title: str
    sheet_names: list[str] | None = None
