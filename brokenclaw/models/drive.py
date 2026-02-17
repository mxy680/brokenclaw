from pydantic import BaseModel


class DriveFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: str | None = None
    created_time: str | None = None
    modified_time: str | None = None
    parents: list[str] | None = None
    web_view_link: str | None = None


class ListFilesResponse(BaseModel):
    files: list[DriveFile]
    result_count: int


class FileContentResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    content: str


class CreateFileRequest(BaseModel):
    name: str
    content: str
    mime_type: str = "text/plain"
    parent_folder_id: str | None = None


class CreateFolderRequest(BaseModel):
    name: str
    parent_folder_id: str | None = None
