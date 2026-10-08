from app.llm.client import MockLLM
from app.llm.schemas import (
    AnalyticsResult,
    ContentResult,
    MontageResult,
    QAReport,
    ResearchResult,
    ScriptResult,
)


def test_mock_returns_valid_structured_output():
    llm = MockLLM()
    user = "Тема: входные двери"
    assert ResearchResult.model_validate(llm.complete("s", user, ResearchResult)).hooks
    assert ScriptResult.model_validate(llm.complete("s", user, ScriptResult)).scenes
    assert ContentResult.model_validate(llm.complete("s", user, ContentResult)).hashtags
    assert MontageResult.model_validate(llm.complete("s", user, MontageResult)).timeline
    assert QAReport.model_validate(llm.complete("s", user, QAReport)).passed is True
    assert AnalyticsResult.model_validate(llm.complete("s", user, AnalyticsResult)).views > 0
