from fastapi import APIRouter

from brokenclaw.models.news import NewsSearchResult
from brokenclaw.services import news as news_service

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/top-headlines")
def top_headlines(
    country: str | None = "us",
    category: str | None = None,
    query: str | None = None,
    page_size: int = 20,
) -> NewsSearchResult:
    return news_service.top_headlines(country, category, query, page_size)


@router.get("/search")
def search_news(
    query: str,
    language: str = "en",
    sort_by: str = "publishedAt",
    from_date: str | None = None,
    to_date: str | None = None,
    domains: str | None = None,
    page_size: int = 20,
) -> NewsSearchResult:
    return news_service.search_news(query, language, sort_by, from_date, to_date, domains, page_size)
