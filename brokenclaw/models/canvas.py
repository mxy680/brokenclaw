from pydantic import BaseModel


class CanvasEvent(BaseModel):
    summary: str
    description: str | None = None
    start: str | None = None
    end: str | None = None
    url: str | None = None
    location: str | None = None
    course: str | None = None


class CanvasUpcoming(BaseModel):
    events: list[CanvasEvent]
    count: int


# --- REST API models ---


class CanvasUserProfile(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    login_id: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class CanvasCourse(BaseModel):
    id: int
    name: str
    course_code: str | None = None
    enrollment_term_id: int | None = None
    start_at: str | None = None
    end_at: str | None = None
    workflow_state: str | None = None
    url: str | None = None


class CanvasAssignment(BaseModel):
    id: int
    name: str
    description: str | None = None
    due_at: str | None = None
    points_possible: float | None = None
    submission_types: list[str] | None = None
    grading_type: str | None = None
    url: str | None = None


class CanvasAnnouncement(BaseModel):
    id: int
    title: str
    message: str | None = None
    posted_at: str | None = None
    author_name: str | None = None
    course_id: int | None = None
    url: str | None = None


class CanvasGrade(BaseModel):
    course_id: int
    course_name: str
    current_score: float | None = None
    final_score: float | None = None
    current_grade: str | None = None
    final_grade: str | None = None


class CanvasSubmission(BaseModel):
    id: int
    assignment_id: int
    submitted_at: str | None = None
    score: float | None = None
    grade: str | None = None
    workflow_state: str | None = None
    late: bool | None = None
    missing: bool | None = None


class CanvasTodoItem(BaseModel):
    type: str | None = None
    assignment_name: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    due_at: str | None = None
    points_possible: float | None = None
    url: str | None = None
