from fastapi import APIRouter

from brokenclaw.models.drive import (
    CreateFileRequest,
    CreateFolderRequest,
    DriveFile,
    FileContentResponse,
    ListFilesResponse,
)
from brokenclaw.services import drive as drive_service

router = APIRouter(prefix="/api/drive", tags=["drive"])


@router.get("/files")
def list_files(max_results: int = 20, account: str = "default") -> ListFilesResponse:
    files = drive_service.list_files(max_results, account=account)
    return ListFilesResponse(files=files, result_count=len(files))


@router.get("/search")
def search_files(query: str, max_results: int = 20, account: str = "default") -> ListFilesResponse:
    files = drive_service.search_files(query, max_results, account=account)
    return ListFilesResponse(files=files, result_count=len(files))


@router.get("/files/{file_id}")
def get_file(file_id: str, account: str = "default") -> DriveFile:
    return drive_service.get_file(file_id, account=account)


@router.get("/files/{file_id}/content")
def get_file_content(file_id: str, account: str = "default") -> FileContentResponse:
    return drive_service.get_file_content(file_id, account=account)


@router.post("/files")
def create_file(request: CreateFileRequest, account: str = "default") -> DriveFile:
    return drive_service.create_file(request.name, request.content, request.mime_type, request.parent_folder_id, account=account)


@router.post("/folders")
def create_folder(request: CreateFolderRequest, account: str = "default") -> DriveFile:
    return drive_service.create_folder(request.name, request.parent_folder_id, account=account)
