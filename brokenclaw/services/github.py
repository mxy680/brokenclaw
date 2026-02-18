import requests

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.github import (
    Issue,
    IssueUser,
    Label,
    Notification,
    PullRequest,
    Repo,
    RepoOwner,
    RepoSearchResult,
)

GITHUB_API_BASE = "https://api.github.com"

HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get_token() -> str:
    token = get_settings().github_token
    if not token:
        raise AuthenticationError(
            "GitHub token not configured. Create a Personal Access Token at "
            "https://github.com/settings/tokens and set GITHUB_TOKEN in .env"
        )
    return token


def _headers() -> dict:
    return {**HEADERS_BASE, "Authorization": f"Bearer {_get_token()}"}


def _handle_response(resp: requests.Response) -> dict | list:
    if resp.status_code == 429:
        raise RateLimitError("GitHub API rate limit exceeded. Try again later.")
    if resp.status_code in (401, 403):
        msg = resp.json().get("message", "Unauthorized")
        if "rate limit" in msg.lower():
            raise RateLimitError(f"GitHub API rate limited: {msg}")
        raise AuthenticationError(f"GitHub auth error: {msg}")
    if resp.status_code == 404:
        raise IntegrationError("GitHub resource not found.")
    if resp.status_code == 422:
        errors = resp.json().get("errors", [])
        raise IntegrationError(f"GitHub validation error: {errors}")
    if resp.status_code >= 400:
        raise IntegrationError(f"GitHub API error ({resp.status_code}): {resp.text[:200]}")
    if resp.status_code == 204:
        return {}
    return resp.json()


def _parse_repo(item: dict) -> Repo:
    owner = item.get("owner", {})
    return Repo(
        id=item["id"],
        name=item["name"],
        full_name=item["full_name"],
        owner=RepoOwner(
            login=owner.get("login", ""),
            avatar_url=owner.get("avatar_url"),
            url=owner.get("html_url"),
        ),
        private=item.get("private", False),
        description=item.get("description"),
        url=item.get("html_url", ""),
        language=item.get("language"),
        stars=item.get("stargazers_count", 0),
        forks=item.get("forks_count", 0),
        open_issues=item.get("open_issues_count", 0),
        default_branch=item.get("default_branch", "main"),
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
        pushed_at=item.get("pushed_at"),
    )


def _parse_issue(item: dict) -> Issue:
    return Issue(
        id=item["id"],
        number=item["number"],
        title=item.get("title", ""),
        body=item.get("body"),
        state=item.get("state", ""),
        user=IssueUser(login=item.get("user", {}).get("login", "")),
        assignees=[IssueUser(login=a.get("login", "")) for a in item.get("assignees", [])],
        labels=[Label(name=l.get("name", ""), color=l.get("color")) for l in item.get("labels", [])],
        comments=item.get("comments", 0),
        is_pull_request="pull_request" in item,
        url=item.get("html_url", ""),
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
        closed_at=item.get("closed_at"),
    )


def _parse_pr(item: dict) -> PullRequest:
    return PullRequest(
        id=item["id"],
        number=item["number"],
        title=item.get("title", ""),
        body=item.get("body"),
        state=item.get("state", ""),
        user=IssueUser(login=item.get("user", {}).get("login", "")),
        assignees=[IssueUser(login=a.get("login", "")) for a in item.get("assignees", [])],
        labels=[Label(name=l.get("name", ""), color=l.get("color")) for l in item.get("labels", [])],
        head_branch=item.get("head", {}).get("ref", ""),
        base_branch=item.get("base", {}).get("ref", ""),
        draft=item.get("draft", False),
        merged=item.get("merged", False),
        merged_at=item.get("merged_at"),
        comments=item.get("comments", 0),
        review_comments=item.get("review_comments", 0),
        commits=item.get("commits", 0),
        additions=item.get("additions", 0),
        deletions=item.get("deletions", 0),
        url=item.get("html_url", ""),
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
    )


# --- Repos ---

def list_repos(
    sort: str = "updated",
    per_page: int = 30,
) -> list[Repo]:
    """List the authenticated user's repositories."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/user/repos",
        headers=_headers(),
        params={"sort": sort, "per_page": min(per_page, 100), "type": "all"},
    )
    data = _handle_response(resp)
    return [_parse_repo(item) for item in data]


def get_repo(owner: str, repo: str) -> Repo:
    """Get a specific repository by owner/repo."""
    resp = requests.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}", headers=_headers())
    return _parse_repo(_handle_response(resp))


def search_repos(query: str, sort: str = "stars", per_page: int = 20) -> RepoSearchResult:
    """Search GitHub repositories."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/search/repositories",
        headers=_headers(),
        params={"q": query, "sort": sort, "per_page": min(per_page, 100)},
    )
    data = _handle_response(resp)
    return RepoSearchResult(
        total_count=data.get("total_count", 0),
        repos=[_parse_repo(item) for item in data.get("items", [])],
    )


# --- Issues ---

def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    per_page: int = 30,
) -> list[Issue]:
    """List issues for a repository (excludes pull requests)."""
    params: dict = {"state": state, "per_page": min(per_page, 100)}
    if labels:
        params["labels"] = labels
    resp = requests.get(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
        headers=_headers(),
        params=params,
    )
    data = _handle_response(resp)
    return [_parse_issue(item) for item in data if "pull_request" not in item]


def get_issue(owner: str, repo: str, issue_number: int) -> Issue:
    """Get a specific issue by number."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}",
        headers=_headers(),
    )
    return _parse_issue(_handle_response(resp))


def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> Issue:
    """Create a new issue."""
    payload: dict = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    resp = requests.post(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
        headers=_headers(),
        json=payload,
    )
    return _parse_issue(_handle_response(resp))


# --- Pull Requests ---

def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> list[PullRequest]:
    """List pull requests for a repository."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
        headers=_headers(),
        params={"state": state, "per_page": min(per_page, 100)},
    )
    data = _handle_response(resp)
    return [_parse_pr(item) for item in data]


def get_pull_request(owner: str, repo: str, pr_number: int) -> PullRequest:
    """Get a specific pull request by number."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
        headers=_headers(),
    )
    return _parse_pr(_handle_response(resp))


# --- Notifications ---

def list_notifications(
    all_notifications: bool = False,
    participating: bool = False,
    per_page: int = 30,
) -> list[Notification]:
    """List notifications for the authenticated user."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/notifications",
        headers=_headers(),
        params={
            "all": str(all_notifications).lower(),
            "participating": str(participating).lower(),
            "per_page": min(per_page, 50),
        },
    )
    data = _handle_response(resp)
    notifications = []
    for item in data:
        subject = item.get("subject", {})
        repo_obj = item.get("repository", {})
        notifications.append(Notification(
            id=item["id"],
            reason=item.get("reason", ""),
            unread=item.get("unread", False),
            subject_title=subject.get("title", ""),
            subject_type=subject.get("type", ""),
            repo_full_name=repo_obj.get("full_name", ""),
            updated_at=item.get("updated_at"),
        ))
    return notifications
