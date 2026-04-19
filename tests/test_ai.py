import pytest


@pytest.mark.asyncio
async def test_summarize_returns_text(monkeypatch):
    """summarize 정상 동작."""
    from unittest.mock import MagicMock
    from app import ai

    fake_client = MagicMock()
    fake_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="요약 결과입니다.")]
    )
    monkeypatch.setattr(ai, "_get_client", lambda: fake_client)

    result = await ai.summarize("대화 내용")
    assert "요약" in result


@pytest.mark.asyncio
async def test_summarize_returns_fallback_on_error(monkeypatch):
    """summarize 예외 시 fallback 반환."""
    from unittest.mock import MagicMock
    from app import ai

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("API 오류")
    monkeypatch.setattr(ai, "_get_client", lambda: fake_client)

    result = await ai.summarize("대화 내용")
    assert result == "(요약 실패)"


@pytest.mark.asyncio
async def test_summarize_without_api_key_returns_fallback(monkeypatch):
    """API 키 없을 때 summarize는 fallback 반환 (크래시 없음)."""
    from app import ai

    def raise_no_key():
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    monkeypatch.setattr(ai, "_get_client", raise_no_key)

    result = await ai.summarize("대화 내용")
    assert result == "(요약 실패)"
