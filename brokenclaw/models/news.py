from pydantic import BaseModel


class ArticleSource(BaseModel):
    id: str | None = None
    name: str


class Article(BaseModel):
    source: ArticleSource
    author: str | None = None
    title: str
    description: str | None = None
    url: str
    image_url: str | None = None
    published_at: str | None = None
    content: str | None = None


class NewsSearchResult(BaseModel):
    total_results: int
    articles: list[Article]
