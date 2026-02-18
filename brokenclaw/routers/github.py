from fastapi import APIRouter

from brokenclaw.models.github import Issue, Notification, PullRequest, Repo, RepoSearchResult
from brokenclaw.services import github as github_service

router = APIRouter(prefix="/api/github", tags=["github"])


@router.get("/repos")
def list_repos(sort: str = "updated", per_page: int = 30) -> list[Repo]:
    return github_service.list_repos(sort, per_page)


@router.get("/repos/{owner}/{repo}")
def get_repo(owner: str, repo: str) -> Repo:
    return github_service.get_repo(owner, repo)


@router.get("/repos/search")
def search_repos(query: str, sort: str = "stars", per_page: int = 20) -> RepoSearchResult:
    return github_service.search_repos(query, sort, per_page)


@router.get("/repos/{owner}/{repo}/issues")
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    per_page: int = 30,
) -> list[Issue]:
    return github_service.list_issues(owner, repo, state, labels, per_page)


@router.get("/repos/{owner}/{repo}/issues/{issue_number}")
def get_issue(owner: str, repo: str, issue_number: int) -> Issue:
    return github_service.get_issue(owner, repo, issue_number)


@router.post("/repos/{owner}/{repo}/issues")
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> Issue:
    return github_service.create_issue(owner, repo, title, body, labels, assignees)


@router.get("/repos/{owner}/{repo}/pulls")
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> list[PullRequest]:
    return github_service.list_pull_requests(owner, repo, state, per_page)


@router.get("/repos/{owner}/{repo}/pulls/{pr_number}")
def get_pull_request(owner: str, repo: str, pr_number: int) -> PullRequest:
    return github_service.get_pull_request(owner, repo, pr_number)


@router.get("/notifications")
def list_notifications(
    all_notifications: bool = False,
    participating: bool = False,
    per_page: int = 30,
) -> list[Notification]:
    return github_service.list_notifications(all_notifications, participating, per_page)
