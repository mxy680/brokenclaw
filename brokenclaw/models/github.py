from pydantic import BaseModel


class RepoOwner(BaseModel):
    login: str
    avatar_url: str | None = None
    url: str | None = None


class Repo(BaseModel):
    id: int
    name: str
    full_name: str
    owner: RepoOwner
    private: bool
    description: str | None = None
    url: str
    language: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    default_branch: str = "main"
    created_at: str | None = None
    updated_at: str | None = None
    pushed_at: str | None = None


class RepoSearchResult(BaseModel):
    total_count: int
    repos: list[Repo]


class IssueUser(BaseModel):
    login: str


class Label(BaseModel):
    name: str
    color: str | None = None


class Issue(BaseModel):
    id: int
    number: int
    title: str
    body: str | None = None
    state: str
    user: IssueUser
    assignees: list[IssueUser] = []
    labels: list[Label] = []
    comments: int = 0
    is_pull_request: bool = False
    url: str
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


class PullRequest(BaseModel):
    id: int
    number: int
    title: str
    body: str | None = None
    state: str
    user: IssueUser
    assignees: list[IssueUser] = []
    labels: list[Label] = []
    head_branch: str
    base_branch: str
    draft: bool = False
    merged: bool = False
    merged_at: str | None = None
    comments: int = 0
    review_comments: int = 0
    commits: int = 0
    additions: int = 0
    deletions: int = 0
    url: str
    created_at: str | None = None
    updated_at: str | None = None


class Notification(BaseModel):
    id: str
    reason: str
    unread: bool
    subject_title: str
    subject_type: str
    repo_full_name: str
    updated_at: str | None = None
