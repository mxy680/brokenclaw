import pytest

from brokenclaw.config import get_settings
from brokenclaw.models.wolfram import WolframResult, WolframShortAnswer
from brokenclaw.services import wolfram as wolfram_service

requires_wolfram = pytest.mark.skipif(
    not get_settings().wolfram_app_id,
    reason="Wolfram Alpha AppID not configured — set WOLFRAM_APP_ID in .env",
)


@requires_wolfram
class TestQuery:
    def test_math_query(self):
        result = wolfram_service.query("integrate x^2 dx")
        assert isinstance(result, WolframResult)
        assert result.success is True
        assert len(result.pods) > 0
        # Should have at least an input interpretation and result pod
        titles = [p.title for p in result.pods]
        assert any("ntegral" in t or "esult" in t or "ndefinite" in t for t in titles)

    def test_factual_query(self):
        result = wolfram_service.query("population of France")
        assert isinstance(result, WolframResult)
        assert result.success is True
        assert len(result.pods) > 0

    def test_conversion_query(self):
        result = wolfram_service.query("100 kg to pounds")
        assert isinstance(result, WolframResult)
        assert result.success is True


@requires_wolfram
class TestShortAnswer:
    def test_simple_question(self):
        result = wolfram_service.short_answer("What is the square root of 144?")
        assert isinstance(result, WolframShortAnswer)
        assert "12" in result.answer

    def test_distance_question(self):
        result = wolfram_service.short_answer("distance from New York to London")
        assert isinstance(result, WolframShortAnswer)
        assert result.answer
