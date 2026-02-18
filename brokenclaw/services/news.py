import requests

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.news import Article, ArticleSource, NewsSearchResult

NEWS_API_BASE = "https://newsapi.org/v2"


def _get_api_key() -> str:
    key = get_settings().news_api_key
    if not key:
        raise AuthenticationError(
            "News API key not configured. Get one at https://newsapi.org and set NEWS_API_KEY in .env"
        )
    return key


def _handle_response(resp: requests.Response) -> dict:
    if resp.status_code == 429:
        raise RateLimitError("News API rate limit exceeded. Try again shortly.")
    if resp.status_code in (401, 403):
        raise AuthenticationError("News API key is invalid. Check NEWS_API_KEY in .env.")
    data = resp.json()
    if data.get("status") == "error":
        code = data.get("code", "")
        message = data.get("message", "")
        if code == "rateLimited":
            raise RateLimitError(f"News API rate limited: {message}")
        if code in ("apiKeyInvalid", "apiKeyDisabled", "apiKeyExhausted"):
            raise AuthenticationError(f"News API key error: {message}")
        raise IntegrationError(f"News API error: {code} — {message}")
    return data


def _parse_articles(data: dict) -> NewsSearchResult:
    articles = []
    for item in data.get("articles", []):
        source = item.get("source", {})
        articles.append(Article(
            source=ArticleSource(id=source.get("id"), name=source.get("name", "")),
            author=item.get("author"),
            title=item.get("title", ""),
            description=item.get("description"),
            url=item.get("url", ""),
            image_url=item.get("urlToImage"),
            published_at=item.get("publishedAt"),
            content=item.get("content"),
        ))
    return NewsSearchResult(
        total_results=data.get("totalResults", 0),
        articles=articles,
    )


def top_headlines(
    country: str | None = "us",
    category: str | None = None,
    query: str | None = None,
    page_size: int = 20,
) -> NewsSearchResult:
    """Get top headlines. Category: business, entertainment, general, health, science, sports, technology."""
    params = {"apiKey": _get_api_key(), "pageSize": min(page_size, 100)}
    if country:
        params["country"] = country
    if category:
        params["category"] = category
    if query:
        params["q"] = query
    resp = requests.get(f"{NEWS_API_BASE}/top-headlines", params=params)
    return _parse_articles(_handle_response(resp))


def search_news(
    query: str,
    language: str = "en",
    sort_by: str = "publishedAt",
    from_date: str | None = None,
    to_date: str | None = None,
    domains: str | None = None,
    page_size: int = 20,
) -> NewsSearchResult:
    """Search all articles. sort_by: relevancy, popularity, publishedAt."""
    params = {
        "apiKey": _get_api_key(),
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "pageSize": min(page_size, 100),
    }
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if domains:
        params["domains"] = domains
    resp = requests.get(f"{NEWS_API_BASE}/everything", params=params)
    return _parse_articles(_handle_response(resp))
