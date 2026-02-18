import pytest

from brokenclaw.config import get_settings
from brokenclaw.models.github import Issue, Notification, PullRequest, Repo, RepoSearchResult
from brokenclaw.services import github as github_service

requires_github = pytest.mark.skipif(
    not get_settings().github_token,
    reason="GitHub token not configured — set GITHUB_TOKEN in .env",
)


@requires_github
class TestListRepos:
    def test_returns_list(self):
        repos = github_service.list_repos(per_page=5)
        assert isinstance(repos, list)
        assert len(repos) > 0
        repo = repos[0]
        assert isinstance(repo, Repo)
        assert repo.full_name
        assert repo.url

    def test_sort_by_updated(self):
        repos = github_service.list_repos(sort="updated", per_page=3)
        assert isinstance(repos, list)


@requires_github
class TestGetRepo:
    def test_get_public_repo(self):
        repo = github_service.get_repo("octocat", "Hello-World")
        assert isinstance(repo, Repo)
        assert repo.full_name == "octocat/Hello-World"
        assert repo.owner.login == "octocat"
        assert repo.url


@requires_github
class TestSearchRepos:
    def test_search(self):
        result = github_service.search_repos("fastapi language:python", per_page=5)
        assert isinstance(result, RepoSearchResult)
        assert result.total_count > 0
        assert len(result.repos) > 0
        assert result.repos[0].full_name


@requires_github
class TestListIssues:
    def test_list_issues_public_repo(self):
        # Use a well-known repo with issues
        issues = github_service.list_issues("octocat", "Hello-World", state="all", per_page=5)
        assert isinstance(issues, list)


@requires_github
class TestListPullRequests:
    def test_list_prs_public_repo(self):
        prs = github_service.list_pull_requests("octocat", "Hello-World", state="all", per_page=5)
        assert isinstance(prs, list)


@requires_github
class TestNotifications:
    def test_list_notifications(self):
        notifs = github_service.list_notifications(per_page=5)
        assert isinstance(notifs, list)


@requires_github
class TestCreateIssue:
    def test_create_and_close_issue(self):
        """Create an issue in the user's own test repo, then close it via the API."""
        # We'll use the first repo the user owns to create a test issue
        repos = github_service.list_repos(per_page=5)
        # Find a repo owned by the authenticated user (not a fork)
        own_repo = None
        for r in repos:
            if not r.private:
                own_repo = r
                break
        if own_repo is None:
            pytest.skip("No public repos found to create a test issue")

        owner, repo_name = own_repo.full_name.split("/", 1)
        issue = None
        try:
            issue = github_service.create_issue(
                owner, repo_name,
                title="[TEST] Brokenclaw integration test — please ignore",
                body="This issue was created by an automated test and should be deleted.",
                labels=[],
            )
            assert isinstance(issue, Issue)
            assert issue.title.startswith("[TEST]")
            assert issue.state == "open"
            assert issue.number > 0
        finally:
            # Close the issue via PATCH
            if issue:
                import requests
                resp = requests.patch(
                    f"https://api.github.com/repos/{owner}/{repo_name}/issues/{issue.number}",
                    headers={
                        "Authorization": f"Bearer {get_settings().github_token}",
                        "Accept": "application/vnd.github+json",
                    },
                    json={"state": "closed"},
                )
                assert resp.status_code == 200
