import pytest

from brokenclaw.config import get_settings
from brokenclaw.models.news import Article, NewsSearchResult
from brokenclaw.services import news as news_service

requires_news = pytest.mark.skipif(
    not get_settings().news_api_key,
    reason="News API key not configured — set NEWS_API_KEY in .env",
)


@requires_news
class TestTopHeadlines:
    def test_us_headlines(self):
        result = news_service.top_headlines(country="us", page_size=5)
        assert isinstance(result, NewsSearchResult)
        assert result.total_results > 0
        assert len(result.articles) > 0
        article = result.articles[0]
        assert isinstance(article, Article)
        assert article.title
        assert article.url

    def test_category_filter(self):
        result = news_service.top_headlines(country="us", category="technology", page_size=5)
        assert isinstance(result, NewsSearchResult)
        assert isinstance(result.articles, list)

    def test_query_filter(self):
        result = news_service.top_headlines(query="AI", page_size=5)
        assert isinstance(result, NewsSearchResult)


@requires_news
class TestSearchNews:
    def test_search(self):
        result = news_service.search_news("artificial intelligence", page_size=5)
        assert isinstance(result, NewsSearchResult)
        assert result.total_results > 0
        assert len(result.articles) > 0
        article = result.articles[0]
        assert article.title
        assert article.url

    def test_sort_by_relevancy(self):
        result = news_service.search_news("climate change", sort_by="relevancy", page_size=5)
        assert isinstance(result, NewsSearchResult)
